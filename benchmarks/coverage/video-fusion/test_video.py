import unittest,json,hashlib,importlib.util
from pathlib import Path
P=Path(__file__).parent;s=importlib.util.spec_from_file_location('fusion',P/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def reports(self):return [json.loads((P/(n+'.json')).read_text()) for n in ['mesa','angle']]
 def test_real_quality(self):
  for r in self.reports():
   self.assertEqual(r['status'],'HOST_PASS');self.assertEqual(len(r['frames']),8);self.assertEqual({(x['frame'],x['mode']) for x in r['frames']},{(f,m) for f in [0,1] for m in ['gpu-nv12','cpu-rgba-fallback','wrong-range','uv-swap']})
   for row in r['frames']:
    self.assertEqual(len(row['pixels']),64);expected,_=m.oracle(*m.validate(m.META,*m.authored(row['frame'])));self.assertEqual(row['cpu_expected'],expected);error=max(abs(a-b) for a,b in zip(row['pixels'],expected));self.assertEqual(error,row['max_byte_error']);self.assertEqual(error<=2,row['mode'] in ['gpu-nv12','cpu-rgba-fallback'])
 def test_stride_padding_not_color(self):
  y,uv=m.authored(0);a=m.validate(m.META,y,uv);y[4]=0;uv[4]=255;self.assertEqual(a,m.validate(m.META,y,uv))
 def test_plane_bounds(self):
  for y,uv in [(m.authored(0)[0][:-1],m.authored(0)[1]),(m.authored(0)[0],m.authored(0)[1]+[0])]:
   with self.assertRaises(ValueError):m.validate(m.META,y,uv)
 def test_byte_and_stride_types(self):
  y,uv=m.authored(0);y[0]=True
  with self.assertRaises(ValueError):m.validate(m.META,y,uv)
  meta=dict(m.META,y_stride=True)
  with self.assertRaises(ValueError):m.validate(meta,*m.authored(0))
 def test_metadata_preflight(self):
  for key,value in [('matrix','BT601'),('range','full'),('siting','cosited'),('reconstruction','bilinear')]:
   with self.assertRaises(ValueError):m.validate(dict(m.META,**{key:value}),*m.authored(0))
 def test_preflight_zero_draw(self):
  for r in self.reports():self.assertEqual(len(r['preflight_rejections']),4);self.assertTrue(all(x['draws']==0 for x in r['preflight_rejections']))
 def test_oracle_endpoints(self):
  self.assertEqual(m.rgb_cpu(16,128,128),[0,0,0]);self.assertEqual(m.rgb_cpu(235,128,128),[1,1,1])
 def test_safe_receipts(self):
  for r in self.reports():self.assertEqual(r['source_sha256'],hashlib.sha256((P/'run.py').read_bytes()).hexdigest());self.assertEqual(r['native_video'],'NOT_RUN');self.assertNotIn('/tmp/',json.dumps(r));self.assertEqual(r['quality_budget'],2)
if __name__=='__main__':unittest.main()
