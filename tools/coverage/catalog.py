"""Offline structural Registry indexing. XML presence is never semantic/runtime proof."""
import hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def write(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,separators=(',',':'),sort_keys=True)+'\n')
def load(manifest,kind):
 from materialize import materialize
 root=Path(manifest).resolve().parents[2]
 if (root/'references/coverage/packed-artifacts.json').is_file():materialize(root)
 m=json.loads(Path(manifest).read_text());wanted='gl.xml' if kind=='gles' else 'egl.xml'
 matches=[s for s in m['sources'] if Path(s['file']).name==wanted]
 if len(matches)!=1:raise ValueError('missing/duplicate frozen source')
 s=matches[0];base=Path(manifest).parent.resolve();p=(base/s['file']).resolve()
 if not p.is_relative_to(base):raise ValueError('source path escape')
 raw=p.read_bytes()
 if sha(raw)!=s['sha256'] or len(raw)!=s['bytes']:raise ValueError('source hash/size mismatch')
 if not re.fullmatch('[a-f0-9]{40}',s['commit']):raise ValueError('unfixed revision')
 if s.get('license_spdx')!='Apache-2.0' or not s.get('license_file'):raise ValueError('license not frozen')
 lic=(base/s['license_file']).resolve()
 if not lic.is_relative_to(base) or sha(lic.read_bytes())!=s.get('license_sha256'):raise ValueError('license hash mismatch')
 return ET.fromstring(raw),s

def blocks(parent):
 return [{'operation':b.tag,'conditions':dict(b.attrib),'commands':[x.get('name') for x in b.findall('command')],
          'enums':[x.get('name') for x in b.findall('enum')],'types':[x.get('name') for x in b.findall('type')]} for b in parent if b.tag in ('require','remove')]
def applies(block,api):
 a=block['conditions'].get('api');profile=block['conditions'].get('profile')
 return (a is None or a==api) and profile in (None,'common')

def category(name):
 for family,words in [('Debug/Robustness',('Debug','Reset','Robust')),('Compute/SSBO/Atomic',('Compute','Storage','Atomic','Barrier')),('Framebuffer/Renderbuffer',('Framebuffer','Renderbuffer')),('Texture/Sampler/Image',('Tex','Sampler','Image')),('Query/Sync',('Query','Sync','Fence','Wait')),('Program/Pipeline',('Program','Shader','Uniform','Pipeline')),('Transform Feedback',('TransformFeedback',)),('Buffer/VAO/Vertex Arrays',('Buffer','Vertex','Attrib')),('Draw/Instancing/Indirect',('Draw','Dispatch','Indirect')),('Raster/Depth/Stencil/Blend',('Blend','Depth','Stencil','Cull','Viewport','Scissor')),('Readback/PixelStore',('ReadPixels','PixelStore'))]:
  if any(w.lower() in name.lower() for w in words):return family
 return 'Limit/State Query or other; semantic classification pending'

def build(manifest,kind):
 root,source=load(manifest,kind);api='gles2' if kind=='gles' else 'egl';allowed={'gles1','gles2'} if kind=='gles' else {'egl'}
 defs={'commands':{},'enums':{}}
 for c in root.findall('./commands/command'):
  name=c.get('name') or c.findtext('proto/name')
  if name:defs['commands'].setdefault(name,[]).append({'attributes':dict(c.attrib),'signature':ET.tostring(c,encoding='unicode').strip(),'aliases':[a.get('name') for a in c.findall('alias')]+([c.get('alias')] if c.get('alias') else [])})
 for c in root.findall('./enums/enum'):
  defs['enums'].setdefault(c.get('name'),[]).append(dict(c.attrib))
 features=[f for f in root.findall('feature') if f.get('api')==api]
 features.sort(key=lambda f:tuple(map(int,f.get('number').split('.'))))
 if [f.get('number') for f in features] != (['2.0','3.0','3.1','3.2'] if kind=='gles' else ['1.0','1.1','1.2','1.3','1.4','1.5']):raise ValueError('incomplete/unreviewed core versions')
 extensions=[]
 for e in root.findall('./extensions/extension'):
  supported=set(e.get('supported','').split('|'))
  if supported&allowed:
   extensions.append({'name':e.get('name'),'namespace':e.get('name').split('_')[1], 'supported':sorted(supported),
      'attributes':dict(e.attrib),'blocks':blocks(e),'coverage_level':'INDEXED_ONLY',
      'rules':[],'examples':[],'tests':[],'semantic_status':'NOT_REVIEWED',
      'source_spec':source['url']+'#'+e.get('name'),'promotion':'NOT_INFERRED_FROM_SUFFIX_OR_ALIAS'})
 entries={k:{} for k in defs};live={k:set() for k in defs};snapshots={}
 def get(k,n):
  if n not in defs[k]:raise ValueError('Registry reference missing definition '+n)
  return entries[k].setdefault(n,{'name':n,'kind':k[:-1],'definitions':defs[k][n], 'aliases':sorted({a for d in defs[k][n] for a in (d.get('aliases',[]) if k=='commands' else [d['alias']] if d.get('alias') else [])}),
   'core_since':None,'core_versions':[],'core_events':[],'extension':[],'rules':[],'examples':[],'tests':[],
   'coverage_level':'INDEXED_ONLY','category':category(n),'category_method':'name heuristic, not semantic validation','source_spec':source['url']+'#'+n})
 for f in features:
  version=f.get('number')
  for b in blocks(f):
   for k in defs:
    for n in b[k]:
     row=get(k,n);row['core_events'].append({'version':version,'feature':f.get('name'),'operation':b['operation'],'conditions':b['conditions'],'applies_to_index_api':applies(b,api)})
     if applies(b,api):
      if b['operation']=='require':live[k].add(n)
      else:live[k].discard(n)
  for k in defs:
   for n in live[k]:
    row=get(k,n);row['core_versions'].append(version)
    if row['core_since'] is None:row['core_since']=version
  snapshots[version]={k:sorted(live[k]) for k in defs}
 for e in extensions:
  for b in e['blocks']:
   if b['conditions'].get('api') not in allowed|{None}:continue
   # Retain api/profile conditional memberships, never flatten them into availability.
   for k in defs:
    for n in b[k]:
     row=get(k,n);row['extension'].append({'name':e['name'],'operation':b['operation'],'conditions':b['conditions']})
 return {'schema_version':1,'api':api,'source':source,'core_snapshots':snapshots,
   'commands':sorted(entries['commands'].values(),key=lambda r:r['name']),'enums':sorted(entries['enums'].values(),key=lambda r:r['name']),
   'extensions':sorted(extensions,key=lambda r:r['name']),
   'scope':'Complete frozen structural core and applicable extension index; semantic/compiled/runtime/device/provider coverage NOT_RUN; alias does not imply callable equivalent or extension promotion'}
