import json
import pathlib
import unittest
import tempfile
from shader_experiments import run, source_path
from shader_risks import analyze
ROOT=pathlib.Path(__file__).parent
class RiskTests(unittest.TestCase):
    def test_experiments(self):
        experiments=json.loads((ROOT/'cases/shader-risk-experiments.json').read_text());self.assertGreaterEqual(len(experiments),8)
        for experiment in experiments:
            with self.subTest(experiment=experiment['id']):
                report=analyze(experiment['source_a'],experiment['id'],variant_count=experiment['variant_count'])
                self.assertTrue(report['risks']);self.assertEqual(report['measurement_status'],'NOT_RUN');self.assertIsNone(experiment['measurements'])
                for risk in report['risks']:
                    self.assertGreaterEqual(risk['line'],1);self.assertTrue(risk['experiment']);self.assertEqual(risk['evidence'],'STATIC_HEURISTIC')
    def test_complete_experiment_sources(self):
        experiments=json.loads((ROOT/'cases/shader-risk-experiments.json').read_text())
        for experiment in experiments:
            for arm in ('a','b'):
                text=source_path(experiment['sources'][arm]).read_text()
                self.assertEqual(text,experiment['source_'+arm])
                self.assertTrue(text.startswith('#version 300 es'))
                self.assertIn('void main()',text)
            self.assertTrue(experiment['input_equivalence'])
        self.assertEqual(sum(row['expected_compile']['a']=='REJECT' for row in experiments),1)
    def test_missing_compiler_persists_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path=pathlib.Path(folder)/'report.json'
            report=run('/nonexistent/gles-compiler',path)
            self.assertEqual(report['status'],'FAIL')
            self.assertEqual(json.loads(path.read_text())['device_measurement_status'],'NOT_RUN')
            self.assertTrue(report['failures'])
    def test_source_path_boundary(self):
        with self.assertRaises(ValueError):source_path('../../README.md')
    def test_comments(self):self.assertEqual(analyze('// if(x) texture(t,u);\n/* texture(t[i],u); */\nvoid main(){}')['risks'],[])
    def test_line_numbers(self):self.assertEqual(analyze('/* first\nsecond */\nif (enabled) {}')['risks'][0]['line'],3)
    def test_no_false_measurement(self):self.assertEqual(analyze('void main(){}')['risks'],[])
    def test_invalid(self):
        for source in (None,'',12):
            with self.assertRaises(ValueError):analyze(source)
        with self.assertRaises(ValueError):analyze('void main(){}',variant_count=True)
        with self.assertRaises(ValueError):analyze('void main(){}',stage='pixel')
if __name__=='__main__':unittest.main()
