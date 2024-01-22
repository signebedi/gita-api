import unittest
from app import app, limiter

class FlaskAppTestCaseWithoutRateLimiting(unittest.TestCase):

    def setUp(self):
        limiter.enabled = False
        self.app = app.test_client()

    def test_valid_request(self):
        response = self.app.get('/api/gita?reference=1&author_id=16')
        self.assertEqual(response.status_code, 200)
        self.assertIn('content', response.get_json())

    def test_invalid_request_no_reference(self):
        response = self.app.get('/api/gita?author_id=16')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_invalid_request_bad_reference(self):
        response = self.app.get('/api/gita?reference=invalid&author_id=16')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

class FlaskAppTestCaseWithRateLimiting(unittest.TestCase):
    
    def setUp(self):
        limiter.enabled = True
        self.app = app.test_client()

    def test_rate_limit(self):
        # Test the rate limit.
        for _ in range(51):  # Assuming the limit is 50 requests per hour
            response = self.app.get('/api/gita?reference=1&author_id=16')

        self.assertEqual(response.status_code, 429)

if __name__ == '__main__':
    unittest.main()
