import unittest
import diagnose

class DiagnosticTests(unittest.TestCase):
    def test_ten_reproductions(self):
        rows=diagnose.reproduce()
        self.assertEqual(len(rows),10)
        self.assertEqual(len({r['id'] for r in rows}),10)
        for row in rows:
            with self.subTest(case=row['id']):
                self.assertTrue(row['reproduced'])
                for key in ('symptom','capture','minimal_reproduction','root_cause','fix','regression'):
                    self.assertTrue(row[key])
                self.assertEqual(row['hardware'],'NOT_RUN')

if __name__ == '__main__':
    unittest.main()
