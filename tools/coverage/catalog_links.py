"""Explicit new semantic-link contract, not a parser or certification of legacy prose."""
import re
from pathlib import Path
from urllib.parse import urlparse
REQUIRED={'id','api_domain','api','version','extension','rule','example','positive_test','negative_test','positive_case','negative_case','level','source_url'}

def check_links(root,catalogs,document):
 root=Path(root).resolve();errors=[];seen=set();linked=set()
 if not isinstance(document,dict) or document.get('schema_version')!=1 or not isinstance(document.get('rows'),list) or not document['rows']:
  return {'status':'INCOMPLETE','errors':['nonempty schema_version1 rows required'],'linked_rows':0,'linked_apis':0}
 for index,row in enumerate(document['rows']):
  try:
   if not isinstance(row,dict) or set(row)!=REQUIRED:raise ValueError('exact semantic-link fields required')
   if not isinstance(row['id'],str) or not row['id'] or row['id'] in seen:raise ValueError('duplicate/missing link id')
   seen.add(row['id'])
   if row['api_domain'] not in catalogs:raise ValueError('unknown API domain')
   cat=catalogs[row['api_domain']];name=row['api'];version=row['version']
   matches=[x for x in cat['commands']+cat['enums'] if x['name']==name]
   if len(matches)!=1:raise ValueError('ghost/ambiguous API')
   if version not in cat['core_snapshots']:raise ValueError('unknown version boundary')
   if row['extension'] is None:
    if version not in matches[0]['core_versions']:raise ValueError('API unavailable in declared core version')
   else:
    ext=next((e for e in cat['extensions'] if e['name']==row['extension']),None)
    if not ext or cat['api'] not in ext['supported'] or not any(b['operation']=='require' and name in b['commands']+b['enums'] and b['conditions'].get('api',cat['api'])==cat['api'] for b in ext['blocks']):raise ValueError('wrong extension/API linkage')
   if row['level'] not in ('MUST','SHOULD','MAY','IMPLEMENTATION_DEPENDENT'):raise ValueError('unknown rule level')
   u=urlparse(row['source_url'])
   if u.scheme!='https' or u.hostname not in ('registry.khronos.org','raw.githubusercontent.com','github.com') or not u.path:raise ValueError('official source reference required')
   if u.hostname in ('raw.githubusercontent.com','github.com') and not u.path.startswith('/KhronosGroup/'):raise ValueError('non-Khronos repository source')
   contents={}
   for key in ('rule','example','positive_test','negative_test'):
    rel=row[key]
    if not isinstance(rel,str) or not rel:raise ValueError('missing path '+key)
    path=(root/rel).resolve()
    if Path(rel).is_absolute() or not path.is_relative_to(root) or not path.is_file():raise ValueError('missing/escaping path '+key)
    contents[key]=path.read_text()
   if name not in contents['rule'] or name not in contents['example']:raise ValueError('orphan rule/example API reference')
   # Explicit case declarations are linked; this is not runtime evidence.
   for key,field,positive in (('positive_test','positive_case',True),('negative_test','negative_case',False)):
    case=row[field]
    if not isinstance(case,str) or not re.fullmatch('[a-zA-Z0-9_-]+',case):raise ValueError('case id required')
    pattern=r'\bexpect\(\s*"'+re.escape(case)+r'"\s*,\s*(GL_[A-Z_]+)\s*\)'
    errors_expected=re.findall(pattern,contents[key])
    declaring_lines=[line for line in contents[key].splitlines() if re.search(pattern,line)]
    if not any(name in line for line in declaring_lines):raise ValueError('case does not reference linked boundary API')
    if len(errors_expected)!=1:raise ValueError('missing/duplicate declared case '+field)
    if (errors_expected[0]=='GL_NO_ERROR')!=positive:raise ValueError('positive/negative assertion polarity mismatch')
   if row['positive_case']==row['negative_case']:raise ValueError('same positive and negative case')
   linked.add((row['api_domain'],name))
  except (ValueError,TypeError,KeyError,OSError) as e:errors.append(f'row {index}: {e}')
 return {'status':'LINK_CONTRACT_PASS' if not errors else 'INCOMPLETE','errors':errors,
  'linked_rows':len(document['rows'])-len(errors),'linked_apis':len(linked),
  'compiled':'NOT_EVALUATED_BY_LINK_CHECK','runtime':'NOT_EVALUATED_BY_LINK_CHECK',
  'scope':'existence, version/extension route and named assertion polarity; not spec-correctness or independent semantic review'}
