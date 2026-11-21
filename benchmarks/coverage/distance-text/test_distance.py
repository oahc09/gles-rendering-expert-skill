import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('distance_scene',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class DistanceTests(unittest.TestCase):
 def test_atlas(self):
  for kind in ('sdf','msdf'):
   a=m.atlas(kind);self.assertEqual(len(a),256);self.assertTrue(all(type(x)==int and 0<=x<=255 for x in a));self.assertEqual(a[3::4],[255]*64)
 def test_independent_median(self):
  a=m.atlas('msdf')
  for i in range(0,256,4):self.assertEqual(sorted(a[i:i+3])[1],min(a[i],a[i+1]))
 def test_signed_euclidean_corner(self):
  self.assertLess(m.atlas('sdf')[0],m.atlas('msdf')[2])
 def test_full_goldens(self):
  for n in (16,32):
   for kind in ('sdf','msdf'):
    a=m.golden(n,kind);self.assertEqual(len(a),n*n*4);self.assertEqual(a[3::4],[255]*(n*n));self.assertEqual(a[(n//2*n+n//2)*4],255);self.assertEqual(a[0],0);self.assertTrue(any(0<x<255 for x in a[::4]))
 def test_domain(self):
  for n,k in [(0,'sdf'),(17,'msdf'),(32,'font')]:
   with self.assertRaises(ValueError):m.golden(n,k)
 def test_distinct_negative_sources(self):
  sources={m.fragment(16,'msdf',a) for a in ('correct','wrong_channel','wrong_threshold','wrong_outline','alpha_fallback')};self.assertEqual(len(sources),5)

class PackagedEvidenceTests(unittest.TestCase):
 def test_full_archived_evidence(self):
  import gzip,hashlib,json
  directory=Path(__file__).with_name('evidence');manifest=json.loads((directory/'manifest.json').read_text())
  self.assertEqual({r['file'] for r in manifest['entries']},{'mesa.json.gz','angle.json.gz'})
  for entry in manifest['entries']:
   compressed=(directory/entry['file']).read_bytes();raw=gzip.decompress(compressed);report=json.loads(raw)
   self.assertEqual(hashlib.sha256(compressed).hexdigest(),entry['compressed_sha256'])
   self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256']);self.assertEqual(len(raw),entry['bytes']);self.assertEqual(len(compressed),entry['compressed_bytes'])
   self.assertEqual(len(report['rows']),18);self.assertEqual(report['draws'],entry['draws']);self.assertEqual(report['status'],'HOST_PASS')
   self.assertEqual(sum(len(r['pixels']) for r in report['rows']),entry['pixel_values'])
   for row in report['rows']:
    self.assertEqual(len(row['pixels']),row['size']**2*4)
    expected=m.golden(row['size'],row['kind']);error=max(abs(a-b) for a,b in zip(expected,row['pixels']))
    self.assertEqual(error,row['max_error']);self.assertEqual(row['quality'],'PASS' if error<=3 else 'FAIL')
 def test_package_determinism(self):
  import gzip,hashlib,json,tempfile
  spec=importlib.util.spec_from_file_location('pack',Path(__file__).with_name('package_evidence.py'));pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
  directory=Path(__file__).with_name('evidence')
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)
   for name in ('mesa','angle'):(out/(name+'.json')).write_bytes(gzip.decompress((directory/(name+'.json.gz')).read_bytes()))
   first=pack.package(out);second=pack.package(out);self.assertEqual(first,second)
   for entry in first['entries']:self.assertEqual((out/entry['file']).read_bytes(),(directory/entry['file']).read_bytes())

if __name__=='__main__':unittest.main()
