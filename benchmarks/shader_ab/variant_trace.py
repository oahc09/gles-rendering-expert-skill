"""Connect existing variant validation and optional exported trace triage, fail closed."""
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
variants=module('ab_variants','benchmarks/pipeline/variants.py')
traces=module('ab_trace','benchmarks/traces/analyze.py')
def variant(source,arm):
 manifest=dict(gles='3.0',features=['unlit'],extensions=[],required_extensions=[],quality='high',macros={})
 return dict(arm=arm,source_sha256=hashlib.sha256(source.encode()).hexdigest(),manifest=manifest,errors=variants.validate(manifest))
def connect(rows,bundle=None):
 result=dict(status='NOT_MEASURED',scope='Optional exported trace triage, not automatic capture or performance acceptance',bindings=[],missing=['matched physical-device trace exports'])
 if bundle is None:return result
 p=Path(bundle);data=json.loads(p.read_text());known={(r['id'],v['arm']):v['source_sha256'] for r in rows for v in r['variants']}
 seen=set()
 for binding in data['bindings']:
  key=(binding['case'],binding['arm'])
  if key in seen or key not in known or binding['source_sha256']!=known[key]:raise ValueError('Unknown, duplicate or stale trace binding')
  seen.add(key)
  path=traces.safe_path(p.parent,binding['manifest']);manifest=json.loads(path.read_text())
  analysis=traces.analyze(manifest,path.parent)
  # Keep raw environment identities and timestamps private. Never return manifest_device.
  result['bindings'].append(dict(case=key[0],arm=key[1],source_sha256=known[key],status=analysis['status'],provenance=analysis['provenance'],source=analysis['source'],hypothesis_categories=[x['category'] for x in analysis['hypotheses']],missing_metrics=analysis['missing_metrics'],performance_improvement='NOT_MEASURED'))
 result.update(status='TRIAGED_NOT_PERFORMANCE_ACCEPTED',missing=['matched interleaved repetitions and physical device acceptance remain required'])
 return result
