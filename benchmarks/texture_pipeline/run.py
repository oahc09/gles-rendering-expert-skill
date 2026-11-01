#!/usr/bin/env python3
"""Build actual libktx runtime transcoder; record host costs, never phone performance."""
import argparse,hashlib,json,math,os,struct,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(ktx,output,sdk=None):
    output.mkdir(parents=True,exist_ok=True)
    report={'status':'FAIL','tool_root':str(ktx),'physical_device':'NOT_RUN','gpu_upload':'NOT_RUN','results':[]}
    with tempfile.TemporaryDirectory(prefix='gles-ktx-') as temp:
        folder=Path(temp);binary=folder/'transcode'
        command=['c++','-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ktx/'include'),str(ROOT/'examples/texture_pipeline/transcode.cpp'),'-L'+str(ktx/'lib'),'-Wl,-rpath,'+str(ktx/'lib'),'-lktx','-o',str(binary)]
        subprocess.run(command,check=True,capture_output=True);report['compile_argv']=command
        # Original opaque gradient, linear UNORM; no downloaded media/licenses.
        pixels=bytes(v for y in range(32) for x in range(32) for v in (x*8,y*8,(x+y)*4))
        ppm=folder/'source.ppm';ppm.write_bytes(b'P6\n32 32\n255\n'+pixels)
        source=output/'source-uastc.ktx2'
        encoded=subprocess.run([str(ktx/'bin/toktx'),'--t2','--encode','uastc','--threads','1','--assign_oetf','linear',str(source),str(ppm)],capture_output=True,text=True,check=True)
        report['encode_stderr']=encoded.stderr;report['source_sha256']=sha(source);report['source_bytes']=source.stat().st_size
        report['source_description']='Original 32x32 RGB gradient x*8,y*8,(x+y)*4; linear UNORM; opaque; one mip.'
        for target in ('astc','etc2','rgba'):
            prefix=output/target
            result=subprocess.run([str(binary),str(source),target,str(prefix)],check=True,capture_output=True,text=True)
            row=json.loads(result.stdout);row['ktx2_sha256']=sha(prefix.with_suffix('.ktx2'))
            decoded=prefix.with_suffix('.rgba')
            if decoded.exists():
                raw=decoded.read_bytes();assert len(raw)==32*32*4
                rgb=bytes(c for i,c in enumerate(raw) if i%4!=3)
                mse=sum((a-b)**2 for a,b in zip(rgb,pixels))/len(pixels)
                row['quality']={'domain':'linear 8bit RGB; CPU decoder; same source/exposure','mse':mse,'psnr_db':None if mse==0 else 10*math.log10(255**2/mse),'max_abs':max(abs(a-b) for a,b in zip(rgb,pixels)),'decoded_sha256':sha(decoded)}
            else:row['quality']={'status':'NOT_RUN_ETC2_DECODER'}
            report['results'].append(row)
        if sdk:
            env=os.environ.copy();env.update(EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',MESA_SHADER_CACHE_DISABLE='true',
                CPLUS_INCLUDE_PATH=str(sdk/'include'),LIBRARY_PATH=str(sdk/'lib/x86_64-linux-gnu'),LD_LIBRARY_PATH=str(sdk/'lib/x86_64-linux-gnu'))
            sample=folder/'sample'
            command=['c++','-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ktx/'include'),str(ROOT/'examples/texture_pipeline/sample.cpp'),'-L'+str(ktx/'lib'),'-Wl,-rpath,'+str(ktx/'lib'),'-lktx','-lEGL','-lGLESv2','-pthread','-o',str(sample)]
            subprocess.run(command,check=True,capture_output=True,env=env);report['sample_compile_argv']=command
            for row in report['results']:
                target=row['target'];rawfile=output/(target+'.gpu.rgba')
                p=subprocess.run([str(sample),str(output/(target+'.ktx2')),str(rawfile)],capture_output=True,text=True,env=env)
                (output/(target+'.sample.log')).write_text(p.stdout+p.stderr)
                if p.returncode:raise RuntimeError('GPU sample failed: '+p.stderr)
                snapshot=json.loads(p.stdout.splitlines()[0])['CapabilitySnapshot']
                raw=rawfile.read_bytes();assert len(raw)==4096
                rgb=bytes(c for i,c in enumerate(raw) if i%4!=3);mse=sum((a-b)**2 for a,b in zip(rgb,pixels))/len(pixels)
                row['software_gl_quality']={'mse':mse,'psnr_db':None if mse==0 else 10*math.log10(255**2/mse),'max_abs':max(abs(a-b) for a,b in zip(rgb,pixels)),
                    'domain':'linear UNORM RGB, nearest fetch, RGBA8 target, dithering off','raw_sha256':sha(rawfile),'renderer':snapshot['gl_renderer']}
                row['gpu_upload']='PASS_SOFTWARE_ONLY'
            report['capability_snapshot']=snapshot;report['gpu_upload']='PASS_SOFTWARE_ONLY'
            report['sample_code_sha256']=sha(ROOT/'examples/texture_pipeline/sample.cpp')
        invalid=folder/'invalid.ktx2';invalid.write_bytes(b'not KTX')
        report['invalid_input_rejected']=subprocess.run([str(binary),str(invalid),'rgba',str(folder/'bad')],capture_output=True).returncode!=0
        report['negative_resource_tests']=[]
        original=source.read_bytes();dfd=struct.unpack_from('<I',original,48)[0]
        for name,offset,value,width in [('hdr-transfer-pq',dfd+14,16,1),('unsupported-dfd-model',dfd+12,255,1),('zero-width',20,0,4),('oversize-width',20,4096,4),('array-layers',32,2,4),('multiple-mips',40,2,4),('invalid-face-count',36,2,4)]:
            changed=bytearray(original);struct.pack_into('<B' if width==1 else '<I',changed,offset,value)
            resource=folder/(name+'.ktx2');resource.write_bytes(changed)
            result=subprocess.run([str(binary),str(resource),'rgba',str(folder/(name+'-output'))],capture_output=True,text=True)
            report['negative_resource_tests'].append({'case':name,'provenance':'mutated synthetic KTX header/DFD, not a real HDR media capture','rejected':result.returncode!=0,'stderr':result.stderr,'input_sha256':sha(resource)})
        grayscale=folder/'gray.pgm';grayscale.write_bytes(b'P5\n32 32\n255\n'+bytes([128])*1024)
        grayktx=folder/'gray.ktx2'
        subprocess.run([str(ktx/'bin/toktx'),'--t2','--encode','uastc','--threads','1','--assign_oetf','linear','--target_type','R',str(grayktx),str(grayscale)],check=True,capture_output=True)
        rejected=subprocess.run([str(binary),str(grayktx),'rgba',str(folder/'gray-output')],capture_output=True,text=True)
        report['negative_resource_tests'].append({'case':'one-component-grayscale','provenance':'actual encoded synthetic grayscale UASTC','rejected':rejected.returncode!=0,'stderr':rejected.stderr,'input_sha256':sha(grayktx)})
        etc1s=folder/'unsupported-etc1s.ktx2'
        subprocess.run([str(ktx/'bin/toktx'),'--t2','--encode','etc1s','--threads','1','--assign_oetf','linear',str(etc1s),str(ppm)],check=True,capture_output=True)
        rejected=subprocess.run([str(binary),str(etc1s),'rgba',str(folder/'etc1s-output')],capture_output=True,text=True)
        report['negative_resource_tests'].append({'case':'unsupported-etc1s','provenance':'actual encoded original ETC1S; this example deliberately supports UASTC only','rejected':rejected.returncode!=0,'stderr':rejected.stderr,'input_sha256':sha(etc1s)})
        srgb=folder/'srgb.ktx2'
        subprocess.run([str(ktx/'bin/toktx'),'--t2','--encode','uastc','--threads','1','--assign_oetf','srgb',str(srgb),str(ppm)],check=True,capture_output=True)
        report['srgb_format_tests']=[]
        for target in ('astc','etc2','rgba'):
            tested=subprocess.run([str(binary),str(srgb),target,str(folder/('srgb-'+target))],capture_output=True,text=True)
            report['srgb_format_tests'].append({'target':target,'pass':tested.returncode==0,'stderr':tested.stderr,'scope':'format/data-length assertions only; no sRGB GPU colorimetric quality claim'})
        report['quality_threshold']={'max_abs_code':24,'mse_max':64,'scope':'Authored acceptance for this smooth 32x32 gradient only; not a universal texture quality standard'}
        qualities=[r.get('software_gl_quality',r['quality']) for r in report['results']]
        complete_quality=all('max_abs' in q and 'mse' in q for q in qualities)
        report['quality_pass']=all(q['max_abs']<=24 and q['mse']<=64 for q in qualities) if complete_quality else None
        report['quality_status']='MEASURED' if complete_quality else 'PARTIAL_ETC2_NOT_MEASURED'
        report['status']=('PASS' if complete_quality else 'PASS_TRANSCODE_ONLY') if report['invalid_input_rejected'] and all(x['rejected'] for x in report['negative_resource_tests']) and all(x['pass'] for x in report['srgb_format_tests']) and len(report['results'])==3 and report['quality_pass'] is not False else 'FAIL'
        report['measurement_limits']=['RSS is whole per-process Linux high-water mark including libktx and CPU ASTC decoder, not isolated allocation or GPU residency.','payload_bytes is actual transcoded image data, not driver VRAM allocation.','load/transcode host wall time is one sample, not a comparative mobile performance claim.']
        report['runtime_library_sha256']=sha(ktx/'lib/libktx.so.4.4.2');report['source_code_sha256']=sha(ROOT/'examples/texture_pipeline/transcode.cpp')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ktx-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--gles-sdk',type=Path);a=p.parse_args();result=run(a.ktx_root,a.output,a.gles_sdk);print(json.dumps({'status':result['status']}));raise SystemExit(0 if result['status'].startswith('PASS') else 1)
