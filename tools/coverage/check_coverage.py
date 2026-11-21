#!/usr/bin/env python3
"""Rebuild fixed structural indices offline; reject drift, never equate indexing to semantics."""
import argparse,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from catalog import build,write,sha
from catalog_links import check_links
from runtime_links import validate as validate_runtime_links

def extensions(gles,egl):
 return {'schema_version':1,'sources':[gles['source'],egl['source']],
  'extensions':sorted([dict(e,registry_api=c['api']) for c in (gles,egl) for e in c['extensions']],key=lambda e:e['name']),
  'coverage_level':'INDEXED_ONLY','semantic':'NOT_RUN','runtime':'NOT_RUN','device':'NOT_RUN','provider':'NOT_RUN'}

def validate_extension_metadata(manifest):
 """Check citation metadata only: no claim that absent prose was verified offline."""
 commit=next(s['commit'] for s in manifest['sources'] if s['repository']=='KhronosGroup/OpenGL-Registry')
 rows=manifest.get('extension_specs',[])
 if len(rows)!=3:raise ValueError('Expected three bounded extension citation records')
 urls=set()
 for item in rows:
  if item.get('distribution')!='not_vendored' or 'file' in item or 'sha256' in item:raise ValueError('Extension prose must not be distributed or claimed offline-verified')
  if item.get('revision')!=commit or not re.fullmatch(r'[0-9a-f]{64}',item.get('retrieved_sha256','')):raise ValueError('Invalid extension revision/retrieval hash metadata')
  prefix='https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/'+commit+'/extensions/'
  url=item.get('url','')
  if not url.startswith(prefix) or not re.fullmatch(r'[A-Za-z0-9_]+/[A-Za-z0-9_]+\.txt',url[len(prefix):]) or url in urls:raise ValueError('Invalid/duplicate pinned extension citation URL')
  if not item.get('summary') or item.get('license_status')!='REDISTRIBUTION_NOT_CONFIRMED' or item.get('verification_scope')!='URL/revision/retrieval-hash metadata only; source text not validated offline':raise ValueError('Missing bounded source/permission status')
  urls.add(url)
 return {'status':'METADATA_ONLY','text_distribution':'not_vendored','offline_text_verification':'NOT_PERFORMED','citation_count':len(rows)}

def check(root):
 root=Path(root);base=root/'references/coverage';errors=[]
 try:
  manifest=json.loads((base/'source-manifest.json').read_text())
  validate_extension_metadata(manifest)
  g=build(base/'source-manifest.json','gles');e=build(base/'source-manifest.json','egl')
  for name,expected in [('gles-api-catalog.json',g),('egl-api-catalog.json',e),('extensions-catalog.json',extensions(g,e))]:
   actual=json.loads((base/name).read_text())
   if actual!=expected:errors.append(name+': structural entry/version/extension/source or coverage claim differs from fixed Registry reconstruction')
  links=check_links(root,{'gles':g,'egl':e},json.loads((base/'semantic-links.json').read_text()))
  if links['errors']:errors.extend(links['errors'])
  runtime_links=validate_runtime_links(root,json.loads((base/'runtime-links.json').read_text()),{'gles':g,'egl':e})
  if runtime_links['errors']:errors.extend(runtime_links['errors'])
 except (OSError,ValueError,KeyError,TypeError,ET.ParseError) as ex:
  return {'status':'INCOMPLETE','errors':[str(ex)],'metrics':{'indexed':None,'semantic':None,'compiled':None,'runtime':None,'device':None,'provider':None},'release_ready':False}
 return {'status':'INDEX_COMPLETE_NOT_SEMANTIC' if not errors else 'INCOMPLETE','errors':errors,
  'metrics':{'indexed':{'complete':not errors,'gles_core':{v:{k:len(n) for k,n in s.items()} for v,s in g['core_snapshots'].items()},'egl_core':{v:{k:len(n) for k,n in s.items()} for v,s in e['core_snapshots'].items()},'applicable_extensions':len(g['extensions'])+len(e['extensions']),'extension_denominators':{'modern_gles2':sum('gles2' in x['supported'] for x in g['extensions']),'legacy_only_gles1':sum('gles1' in x['supported'] and 'gles2' not in x['supported'] for x in g['extensions']),'egl':len(e['extensions']),'union':len(g['extensions'])+len(e['extensions'])}},
   'extension_citations':validate_extension_metadata(manifest),'semantic':{'status':'LINKED_NOT_SEMANTIC_ACCEPTANCE','linkage':links},'compiled':{'status':'NOT_RUN'},'runtime':runtime_links,'device':{'status':'NOT_RUN'},'provider':{'status':'NOT_RUN'}},
  'release_ready':False,'limitation':'This checks only frozen Registry structural indexing. Explicit semantic-link contracts are checked separately; legacy linked paths are not acceptance; typed runtime receipts validate four finite archived software API boundaries, not fresh execution or full Registry semantics.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path);a=p.parse_args();r=check(a.root)
 if a.output:write(a.output,r)
 else:print(json.dumps(r,indent=2))
 raise SystemExit(r['status']=='INCOMPLETE')
