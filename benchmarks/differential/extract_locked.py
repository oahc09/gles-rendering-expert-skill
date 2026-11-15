"""Extract only hash-locked library/data files from official browser archive.

Never launch the bundled browser/installer. No path is used from archive input.
"""
import hashlib,json,sys,zipfile
from pathlib import Path

def extract(archive, destination, lock):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    if lock.get("archive_sha256") and hashlib.sha256(Path(archive).read_bytes()).hexdigest()!=lock["archive_sha256"]:
        raise ValueError("archive digest mismatch")
    contents={}
    with zipfile.ZipFile(archive) as z:
        for name,want in lock['files'].items():
            if Path(name).name!=name:raise ValueError('invalid lock name')
            matches=[i for i in z.infolist() if i.filename.split('/')[-1]==name]
            if len(matches)!=1:raise ValueError('missing/duplicate '+name)
            i=matches[0]
            if not 0<i.file_size<=100*1024*1024:raise ValueError('size limit')
            data=z.read(i)
            if hashlib.sha256(data).hexdigest()!=want:raise ValueError('digest mismatch '+name)
            contents[name]=data
    for name,data in contents.items():(destination/name).write_bytes(data)
    return sorted(contents)
if __name__=='__main__':
    lock=json.loads(Path(__file__).with_name('driver-lock.json').read_text())
    print(extract(sys.argv[1],sys.argv[2],lock))
