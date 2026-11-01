import unittest
from validate_shaders import expected_result

class ShaderOutcomeTests(unittest.TestCase):
    def test_compile_error_is_expected_rejection(self):
        self.assertTrue(expected_result(2, False, 'ERROR: illegal GLSL'))
    def test_link_error_is_expected_rejection(self):
        self.assertTrue(expected_result(3, False, 'ERROR: interface mismatch'))
    def test_signal_is_not_rejection(self):
        self.assertFalse(expected_result(-11, False, 'ERROR: crashed'))
    def test_missing_file_is_not_rejection(self):
        self.assertFalse(expected_result(1, False, 'ERROR: cannot open'))
    def test_silent_exit_is_not_rejection(self):
        self.assertFalse(expected_result(2, False, ''))
    def test_positive_needs_success(self):
        self.assertTrue(expected_result(0, True, ''))
        self.assertFalse(expected_result(2, True, 'ERROR: invalid'))

if __name__ == '__main__': unittest.main()
