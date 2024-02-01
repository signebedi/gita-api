import unittest
from gita import (
    validate_ref_type,
    get_reference,
    perform_fuzzy_search,
)
import pandas as pd

class TestReferenceSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load the dataframes if needed
        global df
        df = pd.read_json('data/gita/cleaned_data.json')

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
        result = get_reference("verse", 1, 1, None, 16, df)
        self.assertIn("author", result)
        self.assertIn("text", result)
        self.assertEqual(result["chapter"], "1")
        self.assertEqual(result["verses"], "1")

    def test_get_reference_valid_range(self):
        result = get_reference("range", 1, 1, 3, 16, df)
        self.assertIn("author", result)
        self.assertIn("text", result)
        self.assertEqual(result["chapter"], "1")
        self.assertEqual(result["verses"], "1-3")

    def test_get_reference_range_no_verses_found(self):
        with self.assertRaises(ValueError):
            get_reference("range", 100, 1, 3, 16, df)

    def test_get_reference_invalid_ref_type(self):
        with self.assertRaises(ValueError):
            get_reference("invalid_type", 1, 1, None, 16, df)

    def test_get_reference_invalid_author_id(self):
        with self.assertRaises(ValueError):
            get_reference("range", 1, 1, None, 24, df)

    def test_get_reference_invalid_author_type(self):
        with self.assertRaises(ValueError):
            get_reference("range", 1, 1, 2, "invalid_type", df)

    def test_get_reference_invalid_range_for_null_range_end(self):
        with self.assertRaises(ValueError):
            get_reference("range", 1, 1, None, 16, df)

    def test_get_reference_chapter_all_verses(self):
        result = get_reference("chapter", 1, None, None, 16, df)
        self.assertIn("author", result)
        self.assertIn("text", result)
        self.assertEqual(result["chapter"], "1")
        self.assertEqual(result["verses"], "All")


    def test_invalid_negative_chapter(self):
        with self.assertRaises(ValueError):
            validate_ref_type("-1")

    def test_range_with_equal_start_end(self):
        with self.assertRaises(ValueError):
            validate_ref_type("3.5-5")

    def test_chapter_with_extra_characters(self):
        with self.assertRaises(ValueError):
            validate_ref_type("5a")

    def test_nonexistent_verse_in_existing_chapter(self):
        with self.assertRaises(ValueError):
            get_reference("verse", 1, 999, None, 16, df)

    def test_chapter_no_translation_for_valid_author(self):
        # Assuming chapter 1 has no translation for author ID 999
        with self.assertRaises(ValueError):
            get_reference("chapter", 1, None, None, 999, df)

    def test_valid_range_across_non_sequential_verses(self):
        # Modify this test according to your data's specifics
        result = get_reference("range", 2, 1, 5, 16, df)
        self.assertIn("author", result)
        self.assertIn("text", result)

    def test_chapter_and_verse_as_string(self):
        with self.assertRaises(ValueError):
            get_reference("verse", "1", "1", None, 16, df)


class TestFuzzySearch(unittest.TestCase):
    
    def setUp(self):
        # Mock DataFrame
        self.data = {
            'description': [
                'This is a sample description about Python.',
                'Another description related to Java.',
                'Data analysis with Python and Pandas.',
                'Machine Learning and AI concepts.',
                'Introduction to Java for beginners.'
            ],
            'author_id': [16, 16, 17, 16, 17],
            'full_ref': ['ref1', 'ref2', 'ref3', 'ref4', 'ref5'],
            'authorName': ['Author A', 'Author A', 'Author B', 'Author A', 'Author B']
        }
        self.df = pd.DataFrame(self.data)

    def test_matching_records(self):
        # Test with a query that should match some records
        output = perform_fuzzy_search('Python', self.df, author_id=16, threshold=10)
        self.assertTrue(all(score >= 10 for score in output['match_scores']))

    def test_no_matching_records(self):
        # Test with a query that should not match any records
        with self.assertRaises(ValueError):
            perform_fuzzy_search('Ruby', self.df, author_id=16, threshold=10)

    def test_author_id_filtering(self):
        # Test filtering by author_id
        output = perform_fuzzy_search('Java', self.df, author_id=17, threshold=10)
        self.assertEqual(len(output['text']), 2)

    def test_threshold_boundary(self):
        # Test threshold boundary condition
        output = perform_fuzzy_search('Python', self.df, author_id=16, threshold=50)
        self.assertTrue(all(score >= 50 for score in output['match_scores']))

    def test_max_match_score(self):
        # Test that match score does not exceed 100
        output = perform_fuzzy_search('Python', self.df, author_id=16, threshold=10)
        self.assertTrue(all(score <= 100 for score in output['match_scores']))

    def test_result_ordering(self):
        # Test that results are sorted by match score
        output = perform_fuzzy_search('Python', self.df, author_id=16, threshold=10)
        self.assertTrue(output['match_scores'] == sorted(output['match_scores'], reverse=True))

    def test_result_limit(self):
        # Test that no more than 15 records are returned
        large_df = pd.concat([self.df] * 10, ignore_index=True)
        output = perform_fuzzy_search('Python', large_df, author_id=16, threshold=10)
        self.assertTrue(len(output['text']) <= 15)


if __name__ == '__main__':
    unittest.main()
