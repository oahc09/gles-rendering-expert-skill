import json,unittest
from pathlib import Path
class EGLLifecycle(unittest.TestCase):
 def rows(self,d):return json.loads((Path(__file__).parent/'evidence'/f'{d}.json').read_text())
 def test_both_executed(self):
  for d in ('mesa','angle'):self.assertEqual(self.rows(d)['status'],'HOST_PASS')
 def test_shared_pixel(self):
  for d in ('mesa','angle'):
   r=next(x for x in self.rows(d)['rows'] if x['id']=='shared-texture-readback');self.assertEqual(r['pixel'],[32,64,128,255])
 def test_nonshare(self):
  for d in ('mesa','angle'):self.assertEqual(next(x for x in self.rows(d)['rows'] if x['id']=='nonshared-texture-invisible')['status'],'PASS')
 def test_thread_negative(self):
  for d in ('mesa','angle'):
   r=next(x for x in self.rows(d)['rows'] if x['id']=='cross-thread-current-conflict');self.assertFalse(r['make']);self.assertEqual(r['error'],0x3002)
 def test_error_recovery(self):
  for d in ('mesa','angle'):
   rows=self.rows(d)['rows'];self.assertEqual(next(x for x in rows if x['id']=='invalid-surface-fault')['egl_error'],0x300d);self.assertEqual(next(x for x in rows if x['id']=='recover-after-errors')['status'],'PASS')
 def test_image_sync(self):
  for d in ('mesa','angle'):
   for name in ('egl-image-from-texture','egl-image-destroy','egl-image-invalid-target','egl-fence-sync','egl-sync-destroy'):self.assertEqual(next(x for x in self.rows(d)['rows'] if x['id']==name)['status'],'PASS')
 def test_platform_boundaries(self):self.assertTrue(any('Android' in x for x in self.rows('mesa')['platform_gaps']))
if __name__=='__main__':unittest.main()
