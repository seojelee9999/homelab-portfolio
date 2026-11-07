import base64
import contextlib
import io
import types
import unittest

from bootstrap_secrets import KEYS, PREFIX, ensure_parameters


class Missing(Exception):
    pass


class SSM:
    exceptions = types.SimpleNamespace(ParameterNotFound=Missing)

    def __init__(self):
        self.values = {}
        self.puts = []

    def get_parameter(self, Name, WithDecryption):
        if Name not in self.values:
            raise Missing()
        return {'Parameter': {'Type': 'SecureString', 'Value': self.values[Name]}}

    def put_parameter(self, Name, Value, Type, Overwrite):
        assert Overwrite is False and Type == 'SecureString'
        assert Name not in self.values
        self.values[Name] = Value
        self.puts.append(Name)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.client = SSM()
        self.output = io.StringIO()
        self.capture = contextlib.redirect_stdout(self.output)
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)

    def test_unique_secrets_not_logged_and_rerun_preserves_them(self):
        ensure_parameters(self.client, 'admin@example.com')
        original = self.client.values.copy()
        ensure_parameters(self.client, 'admin@example.com', has_data=True)
        self.assertEqual(original, self.client.values)
        self.assertEqual(len(self.client.puts), len(KEYS))
        self.assertEqual(len(set(original.values())), len(KEYS))
        key = original[PREFIX + 'APP_KEY']
        self.assertEqual(len(base64.b64decode(key[7:])), 32)
        for value in original.values():
            self.assertNotIn(value, self.output.getvalue())

    def test_existing_data_blocks_regenerating_missing_keys(self):
        with self.assertRaisesRegex(RuntimeError, 'restore original secrets'):
            ensure_parameters(self.client, 'admin@example.com', has_data=True)
        self.assertFalse(self.client.puts)

    def test_partial_bootstrap_preserves_existing_key(self):
        key = 'base64:' + base64.b64encode(bytes(range(32))).decode()
        self.client.values[PREFIX + 'APP_KEY'] = key
        ensure_parameters(self.client, 'admin@example.com')
        self.assertEqual(self.client.values[PREFIX + 'APP_KEY'], key)
        self.assertNotIn(PREFIX + 'APP_KEY', self.client.puts)

    def test_email_change_never_replaces_credentials(self):
        ensure_parameters(self.client, 'admin@example.com')
        original = self.client.values.copy()
        with self.assertRaisesRegex(RuntimeError, 'differs'):
            ensure_parameters(self.client, 'different@example.com')
        self.assertEqual(original, self.client.values)

    def test_invalid_encryption_key_stops_before_any_writes(self):
        self.client.values[PREFIX + 'APP_KEY'] = 'unsafe-key'
        with self.assertRaises(RuntimeError):
            ensure_parameters(self.client, 'admin@example.com')
        self.assertFalse(self.client.puts)


if __name__ == '__main__':
    unittest.main()
