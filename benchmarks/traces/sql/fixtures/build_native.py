#!/usr/bin/env python3
"""Original synthetic Perfetto TrackEvent protobuf; no device/user data.
Field numbers verified against google/perfetto v59.1 trace_packet/track_descriptor/
thread_descriptor/track_event .proto definitions. Minimal standard wire encoder,
not a general protobuf library; written fixture remains inspectable with Perfetto.
"""
import hashlib
import json
from pathlib import Path

def varint(value):
    result=bytearray()
    while value>127:result.append((value&127)|128);value>>=7
    result.append(value);return bytes(result)
def field(number,value):
    if isinstance(value,int):return varint(number<<3)+varint(value)
    if isinstance(value,str):value=value.encode()
    return varint((number<<3)|2)+varint(len(value))+value

def generate(directory):
    directory.mkdir(parents=True,exist_ok=True)
    thread=field(1,100)+field(2,101)+field(5,'RenderThread')
    descriptor=field(1,1)+field(2,'RenderThread')+field(4,thread)
    trace=field(1,field(8,1000000000)+field(10,1)+field(13,1)+field(60,descriptor))
    for timestamp,kind,name in [(1000000000,1,'gles.frame'),(1001000000,1,'gles.shader_compile'),(1013000000,2,None),(1030000000,2,None)]:
        event=field(9,kind)+field(11,1)
        if name:event+=field(23,name)
        packet=field(8,timestamp)+field(10,1)+field(58,6)+field(11,event)
        trace+=field(1,packet)
    path=directory/'native-compile-hitch.pftrace';path.write_bytes(trace)
    metadata={'source':'Perfetto','license':'MIT original synthetic TrackEvent fixture; no user/device data','device':'synthetic native protobuf','gpu':'none','driver':'none','backend':'Perfetto TrackEvent',
              'build':'fixture-v105','time_range':[1000000000,1030000000],'provenance':'synthetic','time_domain':'trace_processor_ns','capture_complete':True,'raw_sha256':hashlib.sha256(trace).hexdigest()}
    (directory/'native-compile-hitch.metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return path,metadata
if __name__=='__main__':generate(Path(__file__).parent)
