"""Build deterministic SQLite fixtures; no fixture is represented as a captured device trace."""
import hashlib
import json
from pathlib import Path
import sqlite3

CASES=json.loads(Path(__file__).with_name('cases.json').read_text())
def materialize(case,directory):
    directory.mkdir(parents=True,exist_ok=True);raw=directory/'trace.sqlite'
    if case.get('raw_invalid'):raw.write_bytes(b'SQLite format 3\0TRUNCATED')
    else:
        con=sqlite3.connect(raw)
        con.executescript('''CREATE TABLE slice(id INTEGER,ts INTEGER,dur INTEGER,name TEXT,track_id INTEGER);
        CREATE TABLE thread_track(id INTEGER,utid INTEGER); CREATE TABLE thread(utid INTEGER,name TEXT);
        CREATE TABLE sched(id INTEGER,ts INTEGER,dur INTEGER,utid INTEGER,cpu INTEGER);
        CREATE TABLE gpu_slice(id INTEGER,ts INTEGER,dur INTEGER,name TEXT);
        CREATE TABLE counter(id INTEGER,ts INTEGER,value REAL,track_id INTEGER);
        CREATE TABLE counter_track(id INTEGER,name TEXT,unit TEXT);
        CREATE TABLE stats(name TEXT,severity TEXT,value INTEGER);
        INSERT INTO thread VALUES(1,'RenderThread'); INSERT INTO thread_track VALUES(1,1);''')
        for i,(name,ts,dur) in enumerate(case.get('events',[]),1):con.execute('INSERT INTO slice VALUES(?,?,?,?,1)',(i,ts,dur,name))
        for i,(ts,dur) in enumerate(case.get('gpu',[]),1):con.execute('INSERT INTO gpu_slice VALUES(?,?,?,?)',(i,ts,dur,'synthetic GPU work'))
        for i,(name,unit,ts,value) in enumerate(case.get('counters',[]),1):
            con.execute('INSERT INTO counter_track VALUES(?,?,?)',(i,name,unit));con.execute('INSERT INTO counter VALUES(?,?,?,?)',(i,ts,value,i))
        if case.get('drop_table'):con.execute('DROP TABLE '+case['drop_table'])
        if case.get('missing_duration'):con.execute('ALTER TABLE slice DROP COLUMN dur')
        if case.get('parser_loss'):con.execute("INSERT INTO stats VALUES('ftrace_events_lost','error',1)")
        con.commit();con.close()
    meta=dict(source='synthetic-fixture',license=CASES['license'],device='synthetic host fixture',gpu='none',driver='none',backend='normalized SQLite',build='fixture-v105',
              time_range=[0,200000000],provenance='synthetic',time_domain=case.get('clock','trace_processor_ns'),capture_complete=case.get('capture_complete',True),raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
    if case.get('bad_hash'):meta['raw_sha256']='0'*64
    (directory/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');return raw,meta
