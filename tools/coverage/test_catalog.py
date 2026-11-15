import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from catalog import build,write
from check_coverage import check,extensions
from capability import CapabilityNegotiator
ROOT=Path(__file__).resolve().parents[2];M=ROOT/'references/coverage/source-manifest.json'
class CatalogTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.g=build(M,'gles');cls.e=build(M,'egl')
 def test_counts_and_versions(self):
  self.assertEqual([len(self.g['core_snapshots'][v]['commands']) for v in ('2.0','3.0','3.1','3.2')],[142,246,314,358]);self.assertEqual(len(self.e['core_snapshots']['1.5']['commands']),44)
 def test_deterministic(self):self.assertEqual(self.g,build(M,'gles'))
 def test_alias_and_no_promotion_guess(self):
  r=next(r for r in self.g['commands'] if r['name']=='glDebugMessageCallbackKHR');self.assertIn('glDebugMessageCallback',r['aliases']);self.assertIsNone(r['core_since'])
 def test_all_indexed_only(self):
  for r in self.g['commands']+self.g['enums']:self.assertEqual(r['coverage_level'],'INDEXED_ONLY');self.assertEqual(r['tests'],[])
 def test_real_check(self):self.assertEqual(check(ROOT)['status'],'INDEX_COMPLETE_NOT_SEMANTIC')
 def mutate_catalog(self,mutator):
  # Preserve genuine fixed sources via symlinks, mutate only generated artifact.
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);b=root/'references/coverage';b.mkdir(parents=True);(b/'registry').symlink_to(M.parent/'registry',target_is_directory=True)
   # Source checker rejects escaping symlink: copy the frozen source instead.
   (b/'registry').unlink();import shutil;shutil.copytree(M.parent/'registry',b/'registry');(b/'source-manifest.json').write_bytes(M.read_bytes());(b/'semantic-links.json').write_bytes((M.parent/'semantic-links.json').read_bytes())
   g=copy.deepcopy(self.g);mutator(g);write(b/'gles-api-catalog.json',g);write(b/'egl-api-catalog.json',self.e);write(b/'extensions-catalog.json',extensions(self.g,self.e));return check(root)
 def test_missing_entry(self):self.assertEqual(self.mutate_catalog(lambda c:c['commands'].pop())['status'],'INCOMPLETE')
 def test_wrong_version(self):self.assertEqual(self.mutate_catalog(lambda c:c['commands'][0].update(core_since='0.1'))['status'],'INCOMPLETE')
 def test_wrong_extension(self):self.assertEqual(self.mutate_catalog(lambda c:c['extensions'][0].update(name='GL_FAKE'))['status'],'INCOMPLETE')
 def test_fake_semantics(self):self.assertEqual(self.mutate_catalog(lambda c:c['commands'][0].update(coverage_level='DEVICE_VERIFIED'))['status'],'INCOMPLETE')
 def test_require_remove_lifecycle(self):
  import shutil,xml.etree.ElementTree as ET,hashlib
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);shutil.copytree(M.parent/'registry',b/'registry');manifest=json.loads(M.read_text());path=b/'registry/gl.xml';tree=ET.parse(path)
   features={f.get('number'):f for f in tree.findall('feature') if f.get('api')=='gles2'}
   remove=ET.SubElement(features['3.1'],'remove');ET.SubElement(remove,'enum',name='GL_ACTIVE_TEXTURE')
   require=ET.SubElement(features['3.2'],'require');ET.SubElement(require,'enum',name='GL_ACTIVE_TEXTURE')
   raw=ET.tostring(tree.getroot());path.write_bytes(raw)
   manifest['sources'][0].update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));write(b/'manifest.json',manifest)
   c=build(b/'manifest.json','gles');r=next(r for r in c['enums'] if r['name']=='GL_ACTIVE_TEXTURE')
   self.assertNotIn('3.1',r['core_versions']);self.assertIn('3.2',r['core_versions']);self.assertTrue(any(e['operation']=='remove' for e in r['core_events']))
 def test_bad_limits(self):
  n=CapabilityNegotiator(self.g,'3.1',entrypoints=['glDispatchCompute'])
  for value in (float('nan'),float('inf'),True,-1):
   with self.assertRaises(ValueError):n.negotiate('glDispatchCompute',minimum_limits={'limit':value})
 def test_source_missing(self):
  with tempfile.TemporaryDirectory() as td:self.assertEqual(check(td)['metrics']['indexed'],None)
 def test_core_boundary_and_pointer(self):
  for v,expected in [('3.0','unsupported'),('3.1','core')]:
   n=CapabilityNegotiator(self.g,v,entrypoints=['glDispatchCompute']);self.assertEqual(n.negotiate('glDispatchCompute',probe_pass=True)['classification'],expected)
  self.assertFalse(CapabilityNegotiator(self.g,'3.1').negotiate('glDispatchCompute',probe_pass=True)['usable'])
 def test_runtime_probe_required(self):self.assertEqual(CapabilityNegotiator(self.g,'3.1',entrypoints=['glDispatchCompute']).negotiate('glDispatchCompute')['classification'],'implementation')
 def test_debug_suffix_routes(self):
  n=CapabilityNegotiator(self.g,'3.0',['GL_KHR_debug'],['glDebugMessageCallbackKHR']);self.assertTrue(n.priority('debug_callback',probe_pass=True)['usable'])
  self.assertFalse(n.negotiate('glDebugMessageCallback',extension='GL_KHR_debug',probe_pass=True,dependency_reviewed=True)['usable'])
 def test_external_dependencies(self):
  n=CapabilityNegotiator(self.g,'3.0',['GL_OES_EGL_image_external'],['glEGLImageTargetTexture2DOES'])
  self.assertFalse(n.priority('external_texture',probe_pass=True,essl_version='1.00')['usable'])
  args=dict(probe_pass=True,egl_version='1.4',egl_extensions=['EGL_KHR_image_base'])
  self.assertTrue(n.priority('external_texture',essl_version='1.00',**args)['usable']);self.assertFalse(n.priority('external_texture',essl_version='3.00',**args)['usable'])
 def test_timer_disjoint(self):
  n=CapabilityNegotiator(self.g,'3.0',['GL_EXT_disjoint_timer_query'],['glQueryCounterEXT'])
  self.assertTrue(n.priority('timer_query',probe_pass=True,disjoint=False)['usable']);self.assertFalse(n.priority('timer_query',probe_pass=True,disjoint=True)['usable'])
 def test_limits(self):
  n=CapabilityNegotiator(self.g,'3.1',entrypoints=['glDispatchCompute'])
  self.assertFalse(n.negotiate('glDispatchCompute',probe_pass=True,minimum_limits={'GL_MAX_COMPUTE_WORK_GROUP_INVOCATIONS':128})['usable'])
 def test_egl_boundary(self):
  self.assertFalse(CapabilityNegotiator(self.e,'1.4',entrypoints=['eglCreateImage']).negotiate('eglCreateImage',probe_pass=True)['usable']);self.assertTrue(CapabilityNegotiator(self.e,'1.5',entrypoints=['eglCreateImage']).negotiate('eglCreateImage',probe_pass=True)['usable'])
if __name__=='__main__':unittest.main()
