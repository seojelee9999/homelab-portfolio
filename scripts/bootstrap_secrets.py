#!/usr/bin/env python3
"""Run on cp-01 with its existing homelab-eso AWS profile. Never print values."""
import argparse
import base64
import json
import secrets
import subprocess

PREFIX = '/homelab/portfolio/'
KEYS = ('APP_KEY', 'DB_PASSWORD', 'MARIADB_ROOT_PASSWORD',
        'INITIAL_ADMIN_EMAIL', 'INITIAL_ADMIN_PASSWORD')


def ensure_parameters(client, email, has_data=False):
    existing = {}
    for key in KEYS:
        try:
            parameter = client.get_parameter(Name=PREFIX + key, WithDecryption=True)['Parameter']
            if parameter['Type'] != 'SecureString':
                raise RuntimeError(f'{key} must be a SecureString')
            existing[key] = parameter['Value']
        except client.exceptions.ParameterNotFound:
            pass
    missing = set(KEYS) - existing.keys()
    if missing and has_data:
        raise RuntimeError('Existing PVCs with missing parameters: restore original secrets before proceeding')
    if existing.get('INITIAL_ADMIN_EMAIL', email) != email:
        raise RuntimeError('Initial administrator email differs; existing credentials were preserved')
    if 'APP_KEY' in existing:
        key = existing['APP_KEY']
        if not key.startswith('base64:') or len(base64.b64decode(key[7:], validate=True)) != 32:
            raise RuntimeError('Existing APP_KEY is not a valid 32-byte key')
    for key in ('DB_PASSWORD', 'MARIADB_ROOT_PASSWORD', 'INITIAL_ADMIN_PASSWORD'):
        if key in existing and len(existing[key]) < 24:
            raise RuntimeError(f'Existing {key} is too short')
    if existing.get('DB_PASSWORD') and existing.get('DB_PASSWORD') == existing.get('MARIADB_ROOT_PASSWORD'):
        raise RuntimeError('Database administrator and application passwords must differ')
    for key in KEYS:
        if key in existing:
            print(f'Preserved {PREFIX}{key}')
            continue
        if key == 'APP_KEY':
            value = 'base64:' + base64.b64encode(secrets.token_bytes(32)).decode()
        elif key == 'INITIAL_ADMIN_EMAIL':
            value = email
        else:
            value = secrets.token_urlsafe(32)
        client.put_parameter(Name=PREFIX + key, Value=value, Type='SecureString', Overwrite=False)
        result = client.get_parameter(Name=PREFIX + key, WithDecryption=True)
        if result['Parameter']['Value'] != value:
            raise RuntimeError(f'Parameter verification failed: {key}')
        print(f'Created {PREFIX}{key}')


def main():
    import boto3
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admin-email', default='lsj2sj03@gmail.com')
    parser.add_argument('--profile', default='homelab-eso')
    args = parser.parse_args()
    if '@' not in args.admin_email or args.admin_email == 'admin@admin.com':
        parser.error('Provide a non-factory administrator email')
    result = subprocess.run(['kubectl', '-n', 'portfolio', 'get', 'pvc', '-o', 'json'],
                            check=True, capture_output=True, text=True)
    has_data = bool(json.loads(result.stdout)['items'])
    client = boto3.Session(profile_name=args.profile, region_name='ap-northeast-2').client('ssm')
    ensure_parameters(client, args.admin_email, has_data=has_data)


if __name__ == '__main__':
    main()
