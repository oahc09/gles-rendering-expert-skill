#!/usr/bin/env python3
"""Reproducible real Android source checks; no fabricated headers or target execution.

python compile_sources.py --jdk /path/jdk --android-jar /sdk/platforms/android-35/android.jar \
  --ndk /path/ndk --output /path/report.json
Exit 0: all compilation/link checks passed; 1: failure; 2: missing toolchain.
This does not build an APK, validate resources, run on a device, or certify HDR/AHB.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LEGACY = {
    'egl_context_manager.cpp': 'EGLContextManager',
    'msaa_ontile_resolve.cpp': 'MsaaOnTilePipeline',
    'offscreen_pipeline.cpp': 'OffscreenPipeline',
    'pbo_streaming_upload.cpp': 'PboStreamingUploader',
    'video_texture_pipeline.cpp': 'VideoTexturePipeline',
    'vertex_array_object.hpp': 'Mesh',
}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def invoke(command, timeout=120):
    try:
        result = subprocess.run([str(x) for x in command], capture_output=True, text=True, timeout=timeout)
        return {'command': [str(x) for x in command], 'exit_code': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {'command': [str(x) for x in command], 'exit_code': None, 'stdout': '',
                'stderr': str(exc), 'error_type': type(exc).__name__}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jdk', type=Path, default=Path(os.environ.get('JAVA_HOME', '/missing-jdk')))
    p.add_argument('--android-jar', type=Path, default=Path(os.environ.get('ANDROID_JAR', '/missing-android.jar')))
    p.add_argument('--ndk', type=Path, default=Path(os.environ.get('ANDROID_NDK_ROOT', '/missing-ndk')))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(argv)
    a.jdk = a.jdk.resolve(); a.ndk = a.ndk.resolve(); a.android_jar = a.android_jar.resolve()
    tools = a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'
    javac = a.jdk/'bin/javac'; compiler = tools/'aarch64-linux-android26-clang++'
    report = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'Java --release 17 against official Android API jar and arm64 Android API26 C++17 compile/link only',
              'script_sha256': digest(__file__), 'checks': [], 'device_execution': 'NOT_RUN',
              'APK_assembly': 'NOT_RUN_BY_THIS_SCRIPT', 'HDR_display_validation': 'NOT_RUN',
              'AHardwareBuffer_import_readback': 'NOT_RUN', 'other_abis': 'NOT_RUN'}
    def save(code):
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'status': report['status'], 'report': str(a.output)}))
        return code
    missing = [str(x) for x in (javac, compiler, tools/'llvm-readelf', a.android_jar, a.ndk/'source.properties') if not x.is_file()]
    if missing:
        report.update(status='BLOCKED_BY_TOOLCHAIN', missing=missing)
        return save(2)
    report['tools'] = {'javac': invoke([javac, '-version']), 'clang': invoke([compiler, '--version']),
                       'ndk_source_properties': (a.ndk/'source.properties').read_text(),
                       'android_jar_sha256': digest(a.android_jar)}
    source_files = sorted(HERE.glob('*/src/main/java/**/*.java'))
    report['source_sha256'] = {str(x.relative_to(ROOT)): digest(x) for x in source_files}
    with tempfile.TemporaryDirectory(prefix='gles-android-source-check-') as temporary:
        temp = Path(temporary); classes = temp/'classes'; classes.mkdir()
        java = invoke([javac, '--release', '17', '-Xlint:all', '-classpath', a.android_jar,
                       '-d', classes, *source_files])
        java.update(name='Android-Java-source', status='PASS' if java['exit_code'] == 0 and source_files else 'FAIL',
                    source_files=[str(x.relative_to(ROOT)) for x in source_files],
                    class_sha256={str(x.relative_to(classes)): digest(x) for x in sorted(classes.rglob('*.class'))})
        report['checks'].append(java)
        native_sources = [(ROOT/'examples/validation/egl_smoke.cpp', None)] + [
            (ROOT/'references/examples'/name, kind) for name, kind in LEGACY.items()]
        for index, (source, kind) in enumerate(native_sources):
            report['source_sha256'][str(source.relative_to(ROOT))] = digest(source)
            compile_source = source
            if kind:
                compile_source = temp/f'wrapper-{index}.cpp'
                compile_source.write_text('#define main illustrative_example_main\n#include '+json.dumps(str(source))+
                    '\n#undef main\nvoid instantiate_types() { '+kind+' instance; }\nint main() { return 0; }\n')
            binary = temp/f'android-{index}'
            command = [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic', compile_source,
                       '-lEGL', '-lGLESv3', '-pthread', '-Wl,-z,max-page-size=16384', '-o', binary]
            check = invoke(command)
            check.update(name=str(source.relative_to(ROOT)), status='PASS' if check['exit_code'] == 0 else 'FAIL',
                         instantiated_type=kind, binary_sha256=digest(binary) if binary.exists() else None)
            if binary.exists():
                elf = invoke([tools/'llvm-readelf', '-h', '-lW', binary])
                check['elf'] = elf
                if elf['exit_code'] != 0: check['status'] = 'FAIL'
            report['checks'].append(check)
        # Reuse the native case's own strict cross-link/alignment validation, rather than a mock.
        ahb_report = temp/'ahb.json'
        ahb = invoke([sys.executable, HERE/'surfacevideo/src/main/cpp/cross_compile.py',
                      '--ndk', a.ndk, '--output', ahb_report])
        ahb.update(name='AHardwareBuffer-native-shared-library', status='PASS' if ahb['exit_code'] == 0 else 'FAIL')
        if ahb_report.exists(): ahb['native_report'] = json.loads(ahb_report.read_text())
        report['checks'].append(ahb)
    report['status'] = 'PASS' if all(x['status'] == 'PASS' for x in report['checks']) else 'FAIL'
    return save(0 if report['status'] == 'PASS' else 1)

if __name__ == '__main__':
    raise SystemExit(main())
