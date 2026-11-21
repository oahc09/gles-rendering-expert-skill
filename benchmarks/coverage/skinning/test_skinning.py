import hashlib,importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('skinning_test',HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Skinning(unittest.TestCase):
 def test_independent_positions(self):
  p=m.cpu(1);self.assertEqual(p[:4],[-.125,-.375,0,1]);self.assertEqual(sum(m.WEIGHTS),4);self.assertNotEqual(m.cpu(0),p)
 def test_transposed_matrix_differs(self):self.assertNotEqual(m.matrix(.5,0),m.matrix(.5,0,True))
 def test_gold_geometry(self):
  for pose in (0,1):self.assertEqual(sum(m.golden(pose)[i+1]==255 for i in range(0,1024,4)),64)
 def test_invalid_case_before_gl(self):
  h=object.__new__(m.Host)
  for pose,arm in [(2,'gpu'),(0,'unknown')]:
   with self.assertRaises(ValueError):h.draw(pose,arm)
 def test_saved_real_dual_driver(self):
  for driver in ('mesa','angle'):
   r=json.loads((HERE/'evidence'/f'{driver}.json').read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertEqual(r['draws'],7)
   for row in r['rows']:
    err=max(abs(a-b) for a,b in zip(row['captured_positions'],m.cpu(row['pose'])));self.assertEqual(err,row['position_max_error']);self.assertEqual(len(row['pixels']),1024)
    if row['arm'] in ('gpu','cpu_fallback'):
     self.assertEqual(err,0);self.assertEqual(row['pixels'],m.golden(row['pose']));self.assertEqual(row['quality'],'PASS')
    else:self.assertGreater(err,1e-6);self.assertNotEqual(row['pixels'],m.golden(1));self.assertEqual(row['quality'],'FAIL')
   for pose in (0,1):
    rows=[x for x in r['rows'] if x['pose']==pose and x['arm'] in ('gpu','cpu_fallback')];self.assertEqual(rows[0]['pixels'],rows[1]['pixels'])
 def test_visual_gold_ppm(self):
  for pose in (0,1):
   pixels=m.golden(pose);rgb=bytes(pixels[i+k] for y in reversed(range(16)) for x in range(16) for k in range(3) for i in [(y*16+x)*4])
   self.assertEqual((HERE/f'golden-pose{pose}.ppm').read_bytes(),b'P6\n16 16\n255\n'+rgb)
if __name__=='__main__':unittest.main()
