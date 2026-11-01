#!/usr/bin/env python3
"""Compile/link old examples and instantiate their C++ types; do not run fake mains."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TYPES = {
    'egl_context_manager.cpp': ['EGLContextManager'],
    'msaa_ontile_resolve.cpp': ['MsaaOnTilePipeline'],
    'offscreen_pipeline.cpp': ['OffscreenPipeline'],
    'pbo_streaming_upload.cpp': ['PboStreamingUploader'],
    'video_texture_pipeline.cpp': ['VideoTexturePipeline'],
    'vertex_array_object.hpp': ['Mesh'],
}
env = os.environ.copy()
if env.get('GLES_SDK_ROOT'):
    sdk = Path(env['GLES_SDK_ROOT'])
    for key, value in [('CPLUS_INCLUDE_PATH', sdk/'include'), ('LIBRARY_PATH', sdk/'lib/x86_64-linux-gnu')]:
        env[key] = str(value) + (os.pathsep + env[key] if env.get(key) else '')
results = []
with tempfile.TemporaryDirectory(prefix='gles-legacy-compile-') as folder:
    for name, types in TYPES.items():
        source = ROOT/'references/examples'/name
        # Rename illustrative main, then instantiate top-level types in an unused function.
        # This forces constructor/destructor checking without claiming runtime behavior.
        wrapper = Path(folder)/(name+'.cpp')
        wrapper.write_text('#define main legacy_example_main\n#include '+json.dumps(str(source))+
                           '\n#undef main\nvoid instantiate_types() { '+
                           ' '.join(f'{kind} instance{i};' for i, kind in enumerate(types))+' }\nint main() { return 0; }\n')
        command = [env.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic',
                   str(wrapper), '-lEGL', '-lGLESv2', '-pthread', '-o', str(Path(folder)/(name+'.bin'))]
        run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
        results.append({'file':str(source.relative_to(ROOT)), 'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                        'instantiated_types':types, 'host_compile_link':'PASS' if run.returncode==0 else 'FAIL',
                        'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr,
                        'runtime':'NOT_RUN (PBO separately executed by egl_smoke)',
                        'android_target_compile':'NOT_RUN: no NDK target toolchain'})
print(json.dumps({'scope':'host C++ constructor instantiation + compile/link, not platform runtime',
                  'compiler':subprocess.check_output([env.get('CXX','c++'),'--version'],text=True).splitlines()[0],
                  'results':results},indent=2))
raise SystemExit(any(row['returncode'] for row in results))
