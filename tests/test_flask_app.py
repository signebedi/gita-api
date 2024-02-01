import unittest, os


os.environ['FLASK_ENV'] = 'testing'
from app import app, signatures

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

        # Create a temp API key
        with app.app_context():
            self.api_key = signatures.write_key(scope=['api_key'], expiration=1, active=True, email="john@example.com")

        # Create a headers dict
        self.headers = {
            'X-API-KEY': self.api_key
        }

    def test_valid_request(self):
        response = self.app.get('/api/gita/reference?reference=1&author_id=16', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn('content', response.get_json())

    def test_invalid_request_no_reference(self):
        response = self.app.get('/api/gita/reference?author_id=16', headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_invalid_request_bad_reference(self):
        response = self.app.get('/api/gita/reference?reference=invalid&author_id=16', headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    def test_rate_limit(self):
        # Test the rate limit.
        for _ in range(11):  # Assuming the limit is 10 requests per hour
            response = self.app.get('/api/gita/reference?reference=1&author_id=16', headers=self.headers)

        self.assertEqual(response.status_code, 429)

if __name__ == '__main__':
    unittest.main()
