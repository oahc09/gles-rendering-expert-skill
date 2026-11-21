import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/coverage'))
from priority_boundaries import decide
from run_priority import result_status
class Priorities(unittest.TestCase):
 def test_runtime_failure_cannot_skip(self):
  rows=[dict(family=f,status='PASS') for f in ('sync','eglimage','robustness','astc','msrtt','protected')];rows[4]['status']='FAIL';self.assertEqual(result_status(rows),'FAIL')
 def test_runtime_missing_family_fails(self):self.assertEqual(result_status([]),'FAIL')
 def args(self,f):
  return {
   'sync':dict(egl='1.5',entrypoints=['eglCreateSync','eglClientWaitSync','eglDestroySync'],facts={'current_context':True}),
   'eglimage':dict(egl='1.5',entrypoints=['eglCreateImage','eglDestroyImage'],facts={'owned_complete_2d_texture':True}),
   'robustness':dict(gles='3.2',entrypoints=['glGetGraphicsResetStatus'],facts={'operation':'reset_query_only'}),
   'msrtt':dict(gl_extensions=['GL_EXT_multisampled_render_to_texture'],entrypoints=['glFramebufferTexture2DMultisampleEXT','glRenderbufferStorageMultisampleEXT'],facts={'samples':2,'max_samples':4,'rgba8_2d_complete':True}),
   'astc':dict(gl_extensions=['GL_KHR_texture_compression_astc_ldr'],entrypoints=['glCompressedTexImage2D'],facts={'format':0x93b0,'size':[4,4],'block_bytes':16,'operation':'upload_only'}),
   'protected':dict(egl_extensions=['EGL_EXT_protected_content'],entrypoints=['eglCreateContext'],facts={'protected_context':True,'protected_resource':True,'platform_secure_path':True})}[f]
 def test_six_positive_scoped_policies(self):
  for f in ('sync','eglimage','robustness','msrtt','astc','protected'):self.assertTrue(decide(f,**self.args(f),probe_pass=True)['usable'])
 def test_no_probe_no_use(self):
  for f in ('sync','eglimage','robustness','msrtt','astc','protected'):self.assertFalse(decide(f,**self.args(f))['usable'])
 def test_failed_probe_no_use(self):
  for f in ('sync','eglimage','robustness','msrtt','astc','protected'):self.assertFalse(decide(f,**self.args(f),probe_pass=False)['usable'])
 def test_missing_entrypoint(self):
  for f in ('sync','eglimage','robustness','msrtt','astc','protected'):
   a=self.args(f);a['entrypoints']=[];self.assertFalse(decide(f,**a,probe_pass=True)['usable'])
 def test_sync_client_dependency(self):self.assertFalse(decide('sync',egl_extensions=['EGL_KHR_fence_sync'],entrypoints=['eglCreateSyncKHR','eglClientWaitSyncKHR','eglDestroySyncKHR'],facts={'current_context':True},probe_pass=True)['usable'])
 def test_no_image_ahb_inference(self):
  a=self.args('eglimage');a['facts']={'ahb_supplied':True};self.assertFalse(decide('eglimage',**a,probe_pass=True)['usable'])
 def test_reset_query_not_robust_access(self):
  a=self.args('robustness');a['facts']={'operation':'robust_access'};self.assertFalse(decide('robustness',**a,probe_pass=True)['usable'])
 def test_msrt_limit(self):
  a=self.args('msrtt');a['facts']['samples']=8;self.assertFalse(decide('msrtt',**a,probe_pass=True)['usable'])
 def test_astc_wrong_block(self):
  a=self.args('astc');a['facts']['block_bytes']=15;self.assertFalse(decide('astc',**a,probe_pass=True)['usable'])
 def test_protected_never_downgrades(self):
  a=self.args('protected');a['facts']['protected_context']=False;r=decide('protected',**a,probe_pass=True);self.assertFalse(r['usable']);self.assertIn('never downgrade',r['fallback'])
 def test_unknown_family_rejected(self):self.assertFalse(decide('vrs',probe_pass=True)['usable'])
 def test_runtime_evidence(self):
  for d in ('mesa','angle'):
   r=json.loads((Path(__file__).parent/'evidence'/f'priority-{d}.json').read_text());self.assertEqual(r['status'],'HOST_PROBES_PASS_WITH_UNSUPPORTED');self.assertEqual({x['family'] for x in r['rows'] if x['status']=='PASS'},{'sync','eglimage','robustness','astc'})
if __name__=='__main__':unittest.main()
