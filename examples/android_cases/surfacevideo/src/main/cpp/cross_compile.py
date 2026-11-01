#!/usr/bin/env python3
"""Real Android NDK compile/link + ELF alignment; never executes target binary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--ndk',type=Path,default=Path(os.environ.get('ANDROID_NDK_ROOT','/missing-ndk')));p.add_argument('--output',type=Path,default=HERE/'cross-compile-result.json');a=p.parse_args()
    tool=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin';compiler=tool/'aarch64-linux-android26-clang++'
    if not compiler.is_file():print(json.dumps({'status':'BLOCKED_BY_TOOLCHAIN'}));return 2
    with tempfile.TemporaryDirectory(prefix='gles-ahb-target-') as temp:
        binary=Path(temp)/'libgles_ahb_case.so';source=HERE/'ahb_texture.cpp'
        command=[str(compiler),'-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-fPIC','-shared',str(source),'-landroid','-lEGL','-lGLESv3','-llog','-Wl,--no-undefined','-Wl,-z,max-page-size=16384','-o',str(binary)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=120)
        elf=subprocess.check_output([str(tool/'llvm-readelf'),'-lW',str(binary)],text=True) if result.returncode==0 else ''
        alignments=[int(line.split()[-1],16) for line in elf.splitlines() if line.strip().startswith('LOAD ')]
        stl=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so'
        stl_headers=subprocess.check_output([str(tool/'llvm-readelf'),'-lW',str(stl)],text=True)
        stl_alignments=[int(line.split()[-1],16) for line in stl_headers.splitlines() if line.strip().startswith('LOAD ')]
        alignment_ok=bool(alignments) and bool(stl_alignments) and all(value>=16384 for value in alignments+stl_alignments)
        report={'scope':'Actual arm64-v8a Android API26 shared-library compile/link and ELF alignment; not APK build or device execution',
                'status':'PASS' if result.returncode==0 and alignment_ok else 'FAIL','command':command,'compiler_version':subprocess.check_output([str(compiler),'--version'],text=True),
                'ndk_properties':(a.ndk/'source.properties').read_text(),'source_sha256':sha(source),'script_sha256':sha(__file__),
                'binary_sha256':sha(binary) if binary.exists() else None,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
                'elf_program_headers':elf,'load_alignments':alignments,'libcxx_shared_sha256':sha(stl),'libcxx_shared_program_headers':stl_headers,'libcxx_shared_load_alignments':stl_alignments,'alignment_16k':alignment_ok,'device_runtime':'NOT_RUN','AHB_import_readback':'NOT_RUN','other_abis':'NOT_RUN'}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'alignment_16k':alignment_ok,'device_runtime':'NOT_RUN'}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
