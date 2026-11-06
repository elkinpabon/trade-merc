import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from pulse.api import app


class ApiTests(unittest.TestCase):
    def test_new_account_is_read_only_and_does_not_fake_market_data(self):
        with tempfile.TemporaryDirectory() as directory:
            url = 'sqlite:///' + str(Path(directory) / 'api.db')
            with patch.dict(os.environ, {'PULSE_DATABASE_URL': url}), \
                    patch('pulse.api.Runtime.start'), patch('pulse.api.Runtime.shutdown'):
                with TestClient(app) as client:
                    response = client.get('/api/overview')
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertEqual(data['account']['initial'], 50)
                    self.assertEqual(data['account']['equity'], 50)
                    self.assertEqual(data['health'], 'WARMING')
                    self.assertEqual(data['positions'], [])
                    self.assertEqual(client.get('/api/market').json()['rows'], [])
                    self.assertEqual(client.get('/api/activity').json()['trades'], [])
                    self.assertEqual(client.post('/api/overview', json={'cash':1000}).status_code, 405)
