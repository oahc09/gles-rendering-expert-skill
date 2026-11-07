import copy
import json
import pathlib
import unittest
from variants import validate, generate, cache_key, load_program
ROOT=pathlib.Path(__file__).parent
DEVICE=dict(vendor='Mesa',renderer='test',version='OpenGL ES 3.2',driver='1',backend='native_gles',material_abi='Material-v1',extensions=['GL_A','GL_B'])
class VariantTests(unittest.TestCase):
    def test_cases(self):
        for case in json.loads((ROOT/'cases/variants.json').read_text()):
            with self.subTest(case=case['id']):
                try: valid=not validate(case['input'])
                except ValueError: valid=False
                self.assertEqual(valid,case['valid'])
    def test_budget(self):
        with self.assertRaisesRegex(ValueError,'GENERATION_BUDGET'):generate(['pbr','unlit'],['3.0'],[],['low'],max_candidates=1)
    def test_pruning(self):
        result=generate(['pbr','unlit'],['3.0'],[],['low'],max_variants=1)
        self.assertEqual((len(result['variants']),len(result['rejected']),result['pruned']),(1,1,2))
    def test_key_invalidation(self):
        key=cache_key('source',{'A':'1'},['-O'],DEVICE)
        for field in ('vendor','renderer','version','driver','backend','material_abi'):
            d=copy.deepcopy(DEVICE);d[field]+='changed';self.assertNotEqual(key,cache_key('source',{'A':'1'},['-O'],d))
        for source,macros,options,d in [('changed',{'A':'1'},['-O'],DEVICE),('source',{'A':'2'},['-O'],DEVICE),('source',{'A':'1'},[],DEVICE),('source',{'A':'1'},['-O'],dict(DEVICE,extensions=[]))]: self.assertNotEqual(key,cache_key(source,macros,options,d))
        self.assertEqual(key,cache_key('source',{'A':'1'},['-O'],dict(DEVICE,extensions=['GL_B','GL_A'])))
    def test_cache_paths(self):
        key='a'*64; record=dict(key=key,format=1,binary=b'cache')
        self.assertEqual(load_program(record,key,[1],lambda *a:True,lambda:False)['path'],'binary')
        for rec,formats,loader in [(None,[1],lambda *a:True),(dict(record,key='b'*64),[1],lambda *a:True),(record,[],lambda *a:True),(dict(record,binary=b''),[1],lambda *a:True),(record,[1],lambda *a:False),(record,[1],lambda *a:1/0)]:
            self.assertEqual(load_program(rec,key,formats,loader,lambda:True)['path'],'source')
    def test_cache_envelope_bounds(self):
        record=dict(key='a'*64,format=1,binary=b'12345')
        def forbidden(*args): self.fail('Oversized blob reached GL loader')
        self.assertEqual(load_program(record,'a'*64,[1],forbidden,lambda:True,max_binary_bytes=4)['reason'],'BINARY_TOO_LARGE')
        for key in ('x'*64,'A'*64,'a'*63,'a'*65,None):
            with self.assertRaises(ValueError):load_program(record,key,[1],forbidden,lambda:True)
        for bound in (0,-1,True,64*1024*1024+1):
            with self.assertRaises(ValueError):load_program(record,'a'*64,[1],forbidden,lambda:True,max_binary_bytes=bound)
    def test_explicit_backend_abi(self):
        for field in ('backend','material_abi'):
            device=dict(DEVICE);del device[field]
            with self.assertRaises(ValueError):cache_key('source',{},[],device)
    def test_compile_failure(self):
        with self.assertRaises(RuntimeError):load_program(None,'a'*64,[1],lambda *a:True,lambda:False)
    def test_malformed(self):
        for variant in [None,{},dict(gles='3.0',features='pbr'),dict(gles='3.0',macros={'A':1})]:
            with self.assertRaises(ValueError):validate(variant)
if __name__=='__main__':unittest.main()
