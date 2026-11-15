"""Safe admission and isolated process outcomes; no stress or real reset injection."""
import sys
import signal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from shader_fuzz import isolated as bounded_process
import threading

MAX_BYTES=1024*1024
MAX_SHADER=65536
MAX_WORK=4096
CLASSES=('PASS','EXPECTED_ERROR','UNDEFINED','IMPLEMENTATION_DEPENDENT','TEST_TIMEOUT','HARNESS_FAILURE','DRIVER_FAILURE','UNSUPPORTED','CANCELLED')

class Rejected(ValueError): pass

def integer(n):
    if type(n) is not int or n<0: raise Rejected('non-negative integer required')
    return n

def texture(width,height,channels=4):
    for n in (width,height,channels): integer(n)
    if not width or not height or channels not in (1,2,3,4): raise Rejected('invalid texture dimensions/channels')
    # Division before multiplication is safe in fixed-width implementations too.
    if width>4096 or height>4096 or width>MAX_BYTES//channels//height: raise Rejected('texture quota exceeded')
    return width*height*channels

def shader(data):
    if not isinstance(data,bytes) or len(data)>MAX_SHADER: raise Rejected('shader byte quota/type')
    try: source=data.decode('utf-8')
    except UnicodeError as e: raise Rejected('shader encoding') from e
    if '\x00' in source: raise Rejected('embedded NUL')
    if not source.startswith('#version '): raise Rejected('missing version')
    return source

def dispatch(x,y,z):
    for n in (x,y,z): integer(n)
    if any(n>64 for n in (x,y,z)) or x*y*z>MAX_WORK: raise Rejected('dispatch quota exceeded')
    return x*y*z

def decode_rgba(data,width,height):
    size=texture(width,height)
    if not isinstance(data,bytes) or len(data)!=size: raise Rejected('raw RGBA payload size mismatch')
    return data

class Quota:
    def __init__(self): self.used=0;self.items={};self.next=0
    def allocate(self,size):
        integer(size)
        if size>MAX_BYTES-self.used: raise Rejected('allocation quota exceeded')
        self.next+=1;self.items[self.next]=size;self.used+=size;return self.next
    def release(self,key): self.used-=self.items.pop(key,0)
    def cleanup(self):
        for key in list(self.items): self.release(key)

def controlled_job(action,attempts=1,cancelled=False):
    if type(attempts) is not int or not 1<=attempts<=3: raise Rejected('retry cap')
    quota=Quota();history=[]
    try:
        if cancelled:return {'status':'CANCELLED','attempts':0,'remaining_bytes':0}
        for attempt in range(attempts):
            try:
                action(quota,attempt)
                history.append('PASS');break
            except Rejected: history.append('EXPECTED_ERROR');break
            except TimeoutError: history.append('TEST_TIMEOUT')
            except Exception: history.append('HARNESS_FAILURE');break
            finally: quota.cleanup()
        return {'status':history[-1],'attempts':len(history),'history':history,'remaining_bytes':quota.used}
    finally: quota.cleanup()

def isolated(command,timeout=1,driver_evidence=False,memory_mb=512,log_bytes=65536,env=None):
    """Reuse W1 process-group cleanup and kernel CPU/memory/file quotas.

    Timeout and resource exhaustion are not diagnosed GPU hangs. A signal needs
    separate reviewed driver evidence; authored Python failures are harness faults.
    """
    if not 0<timeout<=30: raise Rejected('timeout budget')
    if type(memory_mb) is not int or not 128<=memory_mb<=4096: raise Rejected('memory budget')
    if type(log_bytes) is not int or not 1024<=log_bytes<=1024*1024: raise Rejected('log budget')
    result=bounded_process(command,timeout,memory_mb,log_bytes,env)
    code=result['exit_code'];evidence=False
    if result['status']=='TEST_TIMEOUT': status='TEST_TIMEOUT';code=None
    elif result['status']=='UNSUPPORTED': status='UNSUPPORTED'
    elif result['status']!='EXITED': status='HARNESS_FAILURE'
    elif code==0: status='PASS'
    elif code<0 and code not in (-signal.SIGXCPU,-signal.SIGXFSZ) and driver_evidence:
        status='DRIVER_FAILURE';evidence=True
    else: status='HARNESS_FAILURE'
    return {'status':status,'exit_code':code,'driver_evidence':evidence,'log':result['log']}

def worker_cancel():
    stop=threading.Event();released=threading.Event()
    def worker():
        quota=Quota()
        try:
            quota.allocate(64)
            stop.wait(.1)
        finally: quota.cleanup();released.set()
    t=threading.Thread(target=worker);t.start();stop.set();t.join(.5)
    return {'status':'CANCELLED' if released.is_set() and not t.is_alive() else 'TEST_TIMEOUT','cleanup':released.is_set()}
