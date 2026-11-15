import gzip,hashlib,json,pathlib,sys,unittest
D=pathlib.Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT/'tools/coverage'))
from cts_results import report
H=lambda b:hashlib.sha256(b).hexdigest()
class ArchiveTests(unittest.TestCase):
 def test_real_archive_integrity(self):
  d=D/'evidence/mesa';r=json.loads((d/'report.json').read_text());raw=gzip.decompress((d/r['artifact']).read_bytes());expected=(d/'expected.txt').read_bytes();cases=expected.decode().splitlines()
  self.assertEqual(len(cases),578);self.assertEqual(len(set(cases)),578)
  self.assertEqual(H(expected),r['expected_sha256']);self.assertEqual(H(raw),r['raw_qpa_sha256']);self.assertEqual(H((d/r['artifact']).read_bytes()),r['artifact_sha256'])
  derived=report(raw,cases,r['process_exit_code'])
  for k,v in derived.items():self.assertEqual(r[k],v,k)
  receipt=(D/'build-receipt.json').read_bytes();b=json.loads(receipt)
  self.assertEqual(r['build_receipt_sha256'],H(receipt));self.assertEqual(r['source_revision'],b['source_revision']);self.assertTrue(b['tracked_source_clean']);self.assertEqual(b['build_exit_code'],0);self.assertEqual(b['configure_exit_code'],0)
  self.assertEqual(b['helper_sha256'],H((ROOT/'tools/coverage/cts_build.py').read_bytes()));self.assertEqual(r['runner_sha256'],H((D/'run.py').read_bytes()))
  self.assertEqual(b['source_revision'],'5bb4c7e83acea0fc73e3333625e4f20542e584d0');self.assertEqual(len(b['executable_sha256']),64)
  for forbidden in [b'/tmp/',b'/workspace/',b'/home/',b'#sessionInfo',b'GL_VENDOR',b'GL_RENDERER']:self.assertNotIn(forbidden,raw)
  self.assertFalse(r['certification_claim']);self.assertFalse(r['device_validation']);self.assertFalse(r['performance_claim'])
if __name__=='__main__':unittest.main()
