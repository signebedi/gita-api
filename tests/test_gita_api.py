import unittest
from app import validate_ref_type, get_reference
import pandas as pd

class TestGitaAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load the dataframes if needed
        global df, df2
        df = pd.read_json('data/translation.json')
        df2 = pd.read_json('data/verse.json')

    # Tests for validate_ref_type
    def test_valid_chapter(self):
        self.assertEqual(validate_ref_type("5"), ('chapter', 5, None, None))

    def test_valid_verse(self):
        self.assertEqual(validate_ref_type("3.2"), ('verse', 3, 2, None))

    def test_valid_range(self):
        self.assertEqual(validate_ref_type("6.4-7"), ('range', 6, 4, 7))

    def test_invalid_format(self):
        with self.assertRaises(ValueError):
            validate_ref_type("invalid")

    def test_invalid_chapter(self):
        with self.assertRaises(ValueError):
            validate_ref_type("19")

    def test_invalid_verse_format(self):
        with self.assertRaises(ValueError):
            validate_ref_type("2.a")

    def test_invalid_range_format(self):
        with self.assertRaises(ValueError):
            validate_ref_type("3.5-4")

    def test_invalid_chapter_in_range(self):
        with self.assertRaises(ValueError):
            validate_ref_type("20.1-2")

    # Tests for get_reference
    def test_get_reference_valid_verse(self):
        result = get_reference("verse", 1, 1, None, 16)
        self.assertIn("author", result)
        self.assertIn("text", result)
        self.assertEqual(result["chapter"], 1)
        self.assertEqual(result["verses"], 1)

    def test_get_reference_valid_range(self):
        result = get_reference("range", 1, 1, 3, 16)
        self.assertIn("author", result)
        self.assertIn("text", result)
        self.assertEqual(result["chapter"], 1)
        self.assertEqual(result["verses"], "1-3")

    def test_get_reference_range_no_verses_found(self):
        with self.assertRaises(ValueError):
            get_reference("range", 100, 1, 3, 16)

    def test_get_reference_invalid_ref_type(self):
        with self.assertRaises(ValueError):
            get_reference("invalid_type", 1, 1, None, 16)

    def test_get_reference_invalid_author_id(self):
        with self.assertRaises(ValueError):
            get_reference("range", 1, 1, None, 24)

    def test_get_reference_invalid_author_type(self):
        with self.assertRaises(ValueError):
            get_reference("range", 1, 1, 2, "invalid_type")

    def test_get_reference_invalid_range_for_null_range_end(self):
        with self.assertRaises(ValueError):
            get_reference("range", 1, 1, None, 16)

    def test_get_reference_chapter_all_verses(self):
        result = get_reference("chapter", 1, None, None, 16)
        self.assertIn("author", result)
        self.assertIn("text", result)
        self.assertEqual(result["chapter"], 1)
        self.assertEqual(result["verses"], "All")

if __name__ == '__main__':
    unittest.main()
