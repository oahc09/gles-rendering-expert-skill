import unittest
import precision_replay as r
class ReplayTests(unittest.TestCase):
 def test_unavailable_no_draw(self):
  def bad(_):raise AssertionError('must not draw')
  row,pix=r.replay({'selected':None},bad,[]);self.assertEqual(row['status'],'UNAVAILABLE');self.assertFalse(row['executed']);self.assertIsNone(pix)
 def test_unknown_format_rejected(self):
  with self.assertRaises(ValueError):r.replay({'selected':'mystery'},lambda _:[],[])
 def test_selected_draw_invoked(self):
  gold=[20,40,60,255]*4096;calls=[]
  def draw(name):calls.append(name);return gold
  row,pix=r.replay({'selected':'RGBA16F'},draw,gold);self.assertEqual(calls,['RGBA16F']);self.assertEqual(row['status'],'PASS')
 def test_selected_quality_rechecked(self):
  row,_=r.replay({'selected':'RGBA8'},lambda _:[200,0,0,255]*4096,[20,40,60,255]*4096);self.assertEqual(row['status'],'FAIL')
 def test_masked_extensions(self):
  scenarios=r.budget_scenarios(['GL_EXT_float_blend','GL_EXT_color_buffer_float','unrelated'],4096)
  masked=next(x for x in scenarios if x[0]=='masked_float_capabilities');self.assertEqual(masked[1],['unrelated'])
 def test_separate_transfer_budget(self):
  row=next(x for x in r.budget_scenarios([],4096) if x[0]=='no_transfer');self.assertEqual(row[2]['max_logical_transfer_bytes'],0);self.assertGreater(row[2]['max_allocation_bytes'],0)
 def test_explicit_size_bound(self):
  row=next(x for x in r.budget_scenarios([],4096) if x[0]=='undersized_limit');self.assertEqual(row[2]['max_renderbuffer_size'],32)
 def test_dispatch_formats(self):
  class Host:
   def draw(self,objects,camera,**kwargs):return kwargs
  self.assertEqual(r.draw_format('RGBA8',[],0,Host(),Host()),{})
  self.assertEqual(r.draw_format('RGBA32F',[],0,Host(),Host()),{'full_float':True})
if __name__=='__main__':unittest.main()
