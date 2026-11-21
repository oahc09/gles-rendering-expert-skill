import importlib.util,tempfile,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[3]/'tools/coverage/android_build.py';s=importlib.util.spec_from_file_location('android_build',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_missing_sdk_never_passes(self):
  with tempfile.TemporaryDirectory() as td:
   r=m.build(Path(td)/'missing',Path(td)/'gradle',Path(td)/'report',True)
   self.assertEqual(r['build'],'BLOCKED_BY_TOOLCHAIN');self.assertIsNone(r['apk']);self.assertEqual(r['install'],'NOT_RUN')
 def test_sanitize(self):
  self.assertNotIn('/workspace/',m.sanitize('error /workspace/private/file.cpp failed',[]))
 def test_not_install(self):
  self.assertEqual(m.inspect('/nonexistent','/nonexistent')['license_acceptance'],'NOT_PERFORMED')

class ArchiveTests(unittest.TestCase):
 def test_probe_archive_nonempty_and_consistent(self):
  import json
  base=Path(__file__).parent;p=base/'source-probes.json'
  self.assertGreater(p.stat().st_size,0)
  data=json.loads(p.read_text());rows=data['observations'];self.assertEqual(len(rows),5)
  self.assertIn('Recovered',data['provenance'])
  urls={r['url']:r for r in rows};self.assertEqual(len(urls),5)
  for r in rows:
   self.assertEqual(r['status'],200);self.assertGreater(int(r['content_length']),0)
   if not r['url'].endswith('.zip'):self.assertEqual(r['bytes_read'],int(r['content_length']))
  gradle=json.loads((base/'gradle.json').read_text());self.assertEqual(urls[gradle['checksum_url']]['published_sha256'],gradle['sha256'])
  plan=json.loads((base/'source-plan.json').read_text());self.assertIn(plan['metadata_url'],urls)
 def test_archived_json_parseable(self):
  import json
  for p in Path(__file__).parent.rglob('*.json'):
   self.assertGreater(p.stat().st_size,0,p);self.assertIsInstance(json.loads(p.read_text()),(dict,list))

if __name__=='__main__':unittest.main()
