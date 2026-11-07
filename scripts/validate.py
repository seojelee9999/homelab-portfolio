#!/usr/bin/env python3
"""Render the actual manifests and check deployment invariants, without a cluster."""
import json
from pathlib import Path
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate():
    rendered = subprocess.check_output(['kubectl', 'kustomize', str(ROOT / 'deploy')], text=True)
    resources = list(yaml.safe_load_all(rendered))
    index = {(r['kind'], r['metadata']['name']): r for r in resources}
    assert len(index) == len(resources), 'Duplicate resources'
    for resource in resources:
        if resource['kind'] != 'Namespace':
            assert resource['metadata']['namespace'] == 'portfolio'
        assert resource['kind'] != 'Secret', 'No plaintext secrets in Git'
        if resource['kind'] in ('Namespace', 'PersistentVolumeClaim'):
            assert resource['metadata']['annotations']['argocd.argoproj.io/sync-options'] == 'Prune=false,Delete=false'
    claim_names = {name for kind, name in index if kind == 'PersistentVolumeClaim'}
    assert len(claim_names) == 2
    for name in claim_names:
        assert index['PersistentVolumeClaim', name]['spec']['storageClassName'] == 'longhorn-database'
    app = index['Deployment', 'portfolio-bookstack']['spec']
    assert app['replicas'] == 1 and app['strategy']['type'] == 'Recreate'
    db = index['StatefulSet', 'portfolio-mariadb']['spec']
    for spec in (app, db):
        pod = spec['template']['spec']
        assert pod['automountServiceAccountToken'] is False
        for volume in pod['volumes']:
            if 'persistentVolumeClaim' in volume:
                assert volume['persistentVolumeClaim']['claimName'] in claim_names
            if 'configMap' in volume:
                assert ('ConfigMap', volume['configMap']['name']) in index
        container = pod['containers'][0]
        assert ':' in container['image'] and not container['image'].endswith(':latest')
        for probe in ('readinessProbe', 'livenessProbe', 'startupProbe'):
            assert probe in container
    container = app['template']['spec']['containers'][0]
    environment = {item['name']: item.get('value') for item in container['env']}
    assert environment['APP_URL'] == 'https://akibaha.shop/portfolio'
    assert environment['SESSION_SECURE_COOKIE'] == 'true'
    assert environment['STORAGE_IMAGE_TYPE'] == 'local_secure_restricted'
    assert '/run/portfolio-ready' in container['readinessProbe']['exec']['command'][-1]
    configmaps = [r['data'] for r in resources if r['kind'] == 'ConfigMap']
    bootstrap = next(data for data in configmaps if '99-portfolio.sh' in data)
    content = next(data for data in configmaps if 'stack.md' in data)
    assert 'authoring.php' in bootstrap and 'authoring.php' in bootstrap['99-portfolio.sh']
    assert set(content) == {'build.md', 'troubleshooting.md', 'learning.md', 'stack.md'}
    assert all(value.strip() for value in content.values())
    assert any(m['mountPath'] == '/portfolio-content' and m['readOnly'] for m in container['volumeMounts'])
    secrets = [r for r in resources if r['kind'] == 'ExternalSecret']
    keys = {d['secretKey'] for r in secrets for d in r['spec']['data']}
    assert keys == {'APP_KEY', 'DB_PASSWORD', 'MARIADB_ROOT_PASSWORD', 'INITIAL_ADMIN_EMAIL', 'INITIAL_ADMIN_PASSWORD'}
    for secret in secrets:
        assert secret['spec']['secretStoreRef']['name'] == 'aws-parameter-store'
        for item in secret['spec']['data']:
            assert item['remoteRef']['key'].startswith('/homelab/portfolio/')
    route = index['HTTPRoute', 'portfolio']['spec']
    assert route['parentRefs'][0]['name'] == 'tunnel-gateway'
    assert route['parentRefs'][0]['namespace'] == 'gateway-system'
    assert route['hostnames'] == ['akibaha.shop']
    redirect, backend = route['rules']
    assert redirect['matches'][0]['path'] == {'type': 'Exact', 'value': '/portfolio'}
    redirect = redirect['filters'][0]['requestRedirect']
    assert redirect['scheme'] == 'https' and redirect['port'] == 443
    assert redirect['path']['replaceFullPath'] == '/portfolio/'
    assert backend['matches'][0]['path'] == {'type': 'PathPrefix', 'value': '/portfolio'}
    assert backend['filters'][0]['urlRewrite']['path']['replacePrefixMatch'] == '/'
    service = index['Service', backend['backendRefs'][0]['name']]
    assert service['spec']['ports'][0]['port'] == backend['backendRefs'][0]['port']
    registration = json.loads((ROOT / 'gitops/apps/portfolio.json').read_text())
    assert registration['manifest_path'] == 'deploy'
    assert registration['namespace'] == 'portfolio'
    assert registration['repoURL'] == 'https://github.com/seojelee9999/homelab-portfolio.git'
    assert registration['targetRevision'] == 'main'
    print(f'PASS: {len(resources)} rendered resources, routing, secret references, storage retention, and readiness gate')


if __name__ == '__main__':
    validate()
