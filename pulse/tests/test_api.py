import os
import hashlib
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from pulse.api import app


class ApiTests(unittest.TestCase):
    def test_new_account_is_read_only_and_does_not_fake_market_data(self):
        salt = secrets.token_bytes(16)
        pin_hash = f'pbkdf2_sha256$120000${salt.hex()}${hashlib.pbkdf2_hmac("sha256", b"test-pin", salt, 120000).hex()}'
        with tempfile.TemporaryDirectory() as directory:
            url = 'sqlite:///' + str(Path(directory) / 'api.db')
            with patch.dict(os.environ, {'PULSE_DATABASE_URL': url, 'PULSE_LOGIN_PIN_HASH':pin_hash,
                                         'PULSE_SESSION_SECRET':'x'*64,'PULSE_COOKIE_SECURE':'true'}), \
                    patch('pulse.api.Runtime.start'), patch('pulse.api.Runtime.shutdown'), \
                    patch('pulse.api.DIST', Path(__file__).resolve().parents[1] / 'web' / 'public'):
                with TestClient(app, base_url='https://testserver') as client:
                    self.assertEqual(client.get('/api/overview').status_code, 401)
                    self.assertEqual(client.get('/api/health').status_code, 401)
                    logo = client.get('/trademerc.png')
                    self.assertEqual(logo.status_code, 200)
                    self.assertEqual(logo.headers['content-type'], 'image/png')
                    self.assertTrue(logo.content.startswith(b'\x89PNG\r\n\x1a\n'))
                    legacy_logo = client.get('/trademerc.ico')
                    self.assertEqual(legacy_logo.status_code, 200)
                    self.assertEqual(legacy_logo.content, logo.content)
                    self.assertEqual(client.post('/api/auth/login', json={'username':'elkinpabon','pin':'wrong'}).status_code, 401)
                    self.assertEqual(client.post('/api/auth/login', headers={'origin':'https://evil.invalid'},
                                                  json={'username':'elkinpabon','pin':'test-pin'}).status_code, 403)
                    self.assertTrue(client.post('/api/auth/login', json={'username':'elkinpabon','pin':'test-pin'}).json()['authenticated'])
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
                    self.assertFalse(client.post('/api/auth/logout').json()['authenticated'])
                    self.assertEqual(client.get('/api/overview').status_code, 401)
