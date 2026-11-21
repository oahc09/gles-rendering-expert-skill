import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from catalog import build
from catalog_links import check_links
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'references/coverage'
class Links(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.c={k:build(BASE/'source-manifest.json',k) for k in ('gles','egl')}
 def setUp(self):self.d=json.loads((BASE/'semantic-links.json').read_text())
 def check_bad(self):self.assertEqual(check_links(ROOT,self.c,self.d)['status'],'INCOMPLETE')
 def test_true_link_contract(self):
  r=check_links(ROOT,self.c,self.d);self.assertEqual(r['status'],'LINK_CONTRACT_PASS');self.assertEqual(r['linked_rows'],24);self.assertEqual(r['runtime'],'NOT_EVALUATED_BY_LINK_CHECK')
 def test_ghost_api(self):self.d['rows'][0]['api']='glGhost';self.check_bad()
 def test_missing_api(self):self.d['rows'][0].pop('api');self.check_bad()
 def test_bad_version(self):
  row=next(r for r in self.d['rows'] if r['api']=='glMapBufferRange');row['version']='2.0';self.check_bad()
 def test_bad_extension(self):self.d['rows'][0]['extension']='GL_KHR_debug';self.check_bad()
 def test_escape(self):self.d['rows'][0]['rule']='../outside.cpp';self.check_bad()
 def test_absolute(self):self.d['rows'][0]['rule']=str((ROOT/self.d['rows'][0]['rule']).resolve());self.check_bad()
 def test_missing_negative(self):self.d['rows'][0]['negative_test']='missing.cpp';self.check_bad()
 def test_unknown_negative_case(self):self.d['rows'][0]['negative_case']='missing_case';self.check_bad()
 def test_wrong_polarity(self):self.d['rows'][0]['negative_case']=self.d['rows'][0]['positive_case'];self.check_bad()
 def test_orphan_rule(self):self.d['rows'][0]['rule']='references/coverage/source-manifest.json';self.check_bad()
 def test_unrelated_existing_api(self):self.d['rows'][0]['api']='glFenceSync';self.check_bad()
 def test_duplicate_id(self):self.d['rows'][1]['id']=self.d['rows'][0]['id'];self.check_bad()
if __name__=='__main__':unittest.main()
