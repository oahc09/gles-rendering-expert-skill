import copy
import json
import pathlib
import unittest
from material import validate,layout_members
ROOT=pathlib.Path(__file__).parent
BASE=json.loads((ROOT/'manifests/pbr-material.json').read_text())
class MaterialTests(unittest.TestCase):
    def test_cases(self):
        for case in json.loads((ROOT/'cases/material.json').read_text()):
            with self.subTest(case=case['id']):
                try: valid=not validate(case['input'])
                except ValueError: valid=False
                self.assertEqual(valid,case['valid'])
    def test_array_layout(self):
        for layout,stride,size in [('std140',16,48),('std430',4,12)]:
            members,total=layout_members([dict(name='a',type='float',array=3)],layout)
            self.assertEqual((members[0]['array_stride'],total),(stride,size))
    def test_matrix(self):
        for layout,stride,size in [('std140',16,32),('std430',8,16)]:
            members,total=layout_members([dict(name='m',type='mat2')],layout)
            self.assertEqual((members[0]['matrix_stride'],total),(stride,size))
    def test_vec3_tail(self):
        members,size=layout_members([dict(name='v',type='vec3'),dict(name='f',type='float')],'std140')
        self.assertEqual((members[1]['offset'],size),(12,16))
    def test_reflection(self):
        self.assertEqual(validate(BASE,reflection=BASE),[])
        bad=copy.deepcopy(BASE);bad['blocks'][0]['members'][1]['offset']=12;bad['samplers'][0]['unit']=2
        errors=validate(BASE,reflection=bad)
        self.assertIn('Material.roughness:REFLECTION_OFFSET',errors);self.assertIn('baseColorTex:REFLECTION_UNIT',errors)
    def test_reflection_semantic_types(self):
        for field, value in [('type', 'int'), ('array', 2), ('row_major', True)]:
            reflected = copy.deepcopy(BASE)
            reflected['blocks'][0]['members'][1][field] = value
            self.assertIn('Material.roughness:REFLECTION_' + field.upper(), validate(BASE, reflection=reflected))
        reflected = copy.deepcopy(BASE)
        del reflected['blocks'][0]['members'][1]['type']
        self.assertIn('Material.roughness:REFLECTION_TYPE', validate(BASE, reflection=reflected))
        reflected = copy.deepcopy(BASE)
        del reflected['samplers']
        self.assertIn('REFLECTION_SAMPLERS_MISSING', validate(BASE, reflection=reflected))
    def test_varying_precision_can_differ(self):
        value = copy.deepcopy(BASE)
        value['interfaces'] = [dict(name='uv', producer=dict(type='vec2', precision='highp'),
                                    consumer=dict(type='vec2', precision='mediump'))]
        self.assertEqual(validate(value), [])
    def test_abi(self):
        bad=copy.deepcopy(BASE);bad['blocks'][0]['members'][1]['type']='int'
        self.assertIn('CROSS_VARIANT_ABI_MISMATCH',validate(bad,baseline=BASE))
    def test_interface_and_location(self):
        value=copy.deepcopy(BASE);value['interfaces']=[dict(name='uv',producer=dict(type='vec2'),consumer=dict(type='vec3'))]
        self.assertIn('uv:SHADER_INTERFACE_MISMATCH',validate(value))
        value['interfaces'][0]['consumer']['type']='vec2'
        self.assertEqual(validate(value),[])
        value['samplers'][0]['location']=0
        self.assertIn('baseColorTex:REFLECTION_LOCATION',validate(value,reflection=BASE))
    def test_named_resource_order_not_abi(self):
        first = copy.deepcopy(BASE)
        first['blocks'].append(dict(copy.deepcopy(first['blocks'][0]), name='Other', binding=1))
        first['samplers'].append(dict(first['samplers'][0], name='otherTex', unit=1))
        second = copy.deepcopy(first)
        second['blocks'].reverse(); second['samplers'].reverse()
        self.assertEqual(validate(first, baseline=second), [])
    def test_location_not_abi(self):
        first=copy.deepcopy(BASE);second=copy.deepcopy(BASE)
        first['samplers'][0]['location']=0;second['samplers'][0]['location']=3
        self.assertEqual(validate(first,baseline=second),[])
    def test_nested_malformed(self):
        for field in ('type', 'format'):
            bad=copy.deepcopy(BASE);bad['samplers'][0][field]=[]
            if field=='type':
                with self.assertRaises(ValueError):validate(bad)
            else:self.assertTrue(validate(bad))
        with self.assertRaises(ValueError):layout_members([dict(name='a',type=[])],'std140')
        with self.assertRaises(ValueError):validate(BASE,reflection={'blocks':[{}]})
    def test_binding_namespaces(self):
        value=copy.deepcopy(BASE);value['gles']='3.1';value['blocks'].append(dict(value['blocks'][0],name='Storage',kind='ssbo'))
        self.assertEqual(validate(value),[])
    def test_malformed(self):
        for value in [None,{},dict(gles='3.0',blocks={},samplers=[])]:
            with self.assertRaises(ValueError):validate(value)
        for member in [dict(name='a',type='float',array=True),dict(name='a',type='mat4',row_major=True),dict(name='a',type='struct')]:
            with self.assertRaises(ValueError):layout_members([member],'std140')
if __name__=='__main__':unittest.main()
