import hashlib,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'tools/coverage'))
from texture_buffer import route,valid_fetch,accepted_route
class BufferTexture(unittest.TestCase):
 def test_exact_capability_route(self):
  names=['glTexBufferEXT','glTexBufferRangeEXT']
  self.assertEqual(route([3,1],['GL_EXT_texture_buffer'],names),'EXT')
  for version,ext,n in [([3,0],['GL_EXT_texture_buffer'],names),([3,2],['GL_OES_texture_buffer'],names),([3,1],['GL_EXT_texture_buffer'],['glTexBuffer','glTexBufferRange']),([3,1],[],names)]:self.assertEqual(route(version,ext,n),'TEXTURE_2D')
 def test_no_undefined_fetch(self):
  self.assertTrue(valid_fetch(3,4))
  for i in [-1,4,True,1.0]:self.assertFalse(valid_fetch(i,4))
 def test_archives_preserve_mismatch(self):
  for name in ['mesa','angle']:
   r=json.loads((HERE/(name+'.json')).read_text());self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest());self.assertEqual(r['policy_sha256'],hashlib.sha256((ROOT/'tools/coverage/texture_buffer.py').read_bytes()).hexdigest())
   self.assertEqual(accepted_route(r),'EXT' if name=='mesa' else 'TEXTURE_2D');self.assertFalse(r['physical_acceptance']);self.assertFalse(r['performance_claim'])
   rows={x['id']:x for x in r['rows']};self.assertEqual(len(rows),12)
   for key,row in rows.items():
    if key=='detach_ignores_offset_size' and name=='angle':self.assertEqual(row['status'],'FAIL');self.assertEqual(row['gl_error'],1281)
    else:self.assertEqual(row['status'],'PASS')
    if 'pixels' in row:self.assertEqual(len(row['pixels']),64);self.assertEqual(row['pixels'],row['expected'])
 def test_partial_never_accepted(self):
  for s in ['FAIL','FALLBACK_PASS','NOT_SUPPORTED',None]:self.assertEqual(accepted_route({'status':s,'facts':{'route':'EXT'}}),'TEXTURE_2D')
