import copy,tempfile,unittest
from pathlib import Path
import image_pipeline as p

class ImageTests(unittest.TestCase):
    def row(self,c):return dict(status='EXECUTED',compile=True,link=True,harness_gl_error=0,pixels=p.cpu_golden(c))
    def test_four_cases_three_sources(self):
        self.assertEqual(len(p.EXPRESSIONS),4)
        self.assertEqual(len({p.source(c,i) for c in p.EXPRESSIONS for i in range(3)}),12)
    def test_golden_pixel_centers(self):
        g=p.cpu_golden('uv-swizzle');self.assertEqual(g[:4],[32,32,64,255]);self.assertEqual(g[-4:],[223,223,64,255])
    def test_premultiplied_alpha_independent(self):self.assertEqual(p.cpu_golden('premultiplied-alpha')[:4],[102,26,77,128])
    def test_reviewed_sources_only(self):
        for c in p.EXPRESSIONS:
            for i in range(3):self.assertEqual(p.validate_source(c,p.source(c,i)),p.source(c,i))
            for edit in ('for(;;){}','discard;','imageStore(x);','#extension GL_EXT_foo:require'):
                with self.assertRaises(ValueError):p.validate_source(c,p.source(c,0).replace('outColor=',edit+'outColor='))
    def test_source_quota(self):
        with self.assertRaises(ValueError):p.validate_source('uv-swizzle','x'*2049)
    def test_two_equal_wrong_outputs_fail(self):
        r=self.row('uv-swizzle');r['pixels']=[0]*64
        self.assertEqual(p.compare('uv-swizzle',[r,r]),'FAIL')
    def test_compile_success_not_image_success(self):
        r=self.row('color-swizzle');r['pixels']=[255]*64
        self.assertEqual(p.compare('color-swizzle',[r,r]),'FAIL')
    def test_peer_tolerance_and_cpu_tolerance(self):
        a=self.row('premultiplied-alpha');b=copy.deepcopy(a);a['pixels'][0]-=1;b['pixels'][0]+=1
        self.assertEqual(p.compare('premultiplied-alpha',[a,b]),'FAIL')
    def test_malformed_pixels_fail(self):
        for pixels in ([0]*63,[True]*64,[float('nan')]*64,[-1]*64):self.assertFalse(p.pixel_match(pixels,[0]*64))
    def test_driver_error_never_passes(self):
        a=self.row('uv-swizzle');a['harness_gl_error']=1282
        self.assertEqual(p.compare('uv-swizzle',[a,a]),'UNKNOWN')
    def test_missing_driver_closed(self):
        with tempfile.TemporaryDirectory() as t:
            r=p.run([],Path(t)/'run');self.assertEqual(r['status'],'BLOCKED_BY_DRIVER');self.assertEqual(r['model_quality'],'NOT_EVALUATED')
    def test_successful_image_oracle(self):
        for c in p.EXPRESSIONS:self.assertEqual(p.compare(c,[self.row(c),self.row(c)]),'PASS')

if __name__=='__main__':unittest.main()
