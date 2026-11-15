import gzip,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/coverage'))
from materialize import materialize
class Materialize(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);p=self.root/'references/coverage';p.mkdir(parents=True);raw=b'original\r\nbytes';packed=gzip.compress(raw,mtime=0);(p/'data.gz').write_bytes(packed);self.row={'path':'references/coverage/data','packed_path':'references/coverage/data.gz','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'packed_sha256':hashlib.sha256(packed).hexdigest(),'packed_bytes':len(packed)};(p/'packed-artifacts.json').write_text(json.dumps({'artifacts':[self.row]}))
 def test_exact_roundtrip(self):self.assertEqual(materialize(self.root)['artifacts'],1);self.assertEqual((self.root/self.row['path']).read_bytes(),b'original\r\nbytes')
 def test_modified_target_not_overwritten(self):
  p=self.root/self.row['path'];p.write_bytes(b'modified')
  with self.assertRaises(ValueError):materialize(self.root)
  self.assertEqual(p.read_bytes(),b'modified')
 def test_changed_archive_rejected(self):
  (self.root/self.row['packed_path']).write_bytes(b'bad')
  with self.assertRaises(ValueError):materialize(self.root)
if __name__=='__main__':unittest.main()
