#!/usr/bin/env python3
"""Register the published portfolio repo in homelab-argocd and verify deployment."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = 'git@github.com:seojelee9999/homelab-argocd.git'
OWNED = ('apps/portfolio.json',)


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def verify_source_checkout(root, registration, env):
    """Require clean source already published on main, before creating any secrets."""
    def git(*arguments):
        return run(['git', '-C', str(root), *arguments], env=env, capture_output=True).stdout.strip()

    if Path(git('rev-parse', '--show-toplevel')).resolve() != root.resolve():
        raise RuntimeError('The portfolio directory must be its own Git repository')
    https_url = registration['repoURL']
    ssh_url = 'git@github.com:' + https_url.removeprefix('https://github.com/')
    if git('remote', 'get-url', 'origin') not in (https_url, ssh_url):
        raise RuntimeError('Portfolio origin does not match the Argo CD source repository')
    if git('branch', '--show-current') != registration['targetRevision']:
        raise RuntimeError('Portfolio checkout must be on main')
    if git('status', '--porcelain'):
        raise RuntimeError('Commit and publish all portfolio source changes first')
    git('fetch', 'origin', 'main')
    revision = git('rev-parse', 'HEAD')
    if revision != git('rev-parse', 'origin/main'):
        raise RuntimeError('Portfolio HEAD must match published origin/main before registration')
    return revision


def application_is_ready(application, registration, revision):
    source = application.get('spec', {}).get('source', {})
    status = application.get('status', {})
    return (source.get('repoURL') == registration['repoURL']
            and source.get('path') == registration['manifest_path']
            and source.get('targetRevision') == registration['targetRevision']
            and status.get('sync', {}).get('status') == 'Synced'
            and status.get('sync', {}).get('revision') == revision
            and status.get('health', {}).get('status') == 'Healthy')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.home() / 'homelab-argocd')
    parser.add_argument('--admin-email', default='lsj2sj03@gmail.com')
    parser.add_argument('--host', default='ubuntu@192.168.55.10')
    parser.add_argument('--ssh-key', type=Path, default=Path.home() / '.ssh/id_ed25519')
    args = parser.parse_args()
    repo = args.repo.resolve()
    ssh = ['ssh', '-F', '/dev/null', '-i', str(args.ssh_key), '-o', 'IdentitiesOnly=yes',
           '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8']
    env = dict(os.environ, GIT_SSH_COMMAND=shlex.join(ssh))

    def git(*arguments, capture=False):
        return run(['git', '-C', str(repo), *arguments], env=env, capture_output=capture).stdout

    def remote(command, **kwargs):
        return run([*ssh, args.host, command], **kwargs)

    run([sys.executable, str(ROOT / 'scripts/validate.py')])
    registration_source = ROOT / 'gitops/apps/portfolio.json'
    registration_config = json.loads(registration_source.read_text())
    expected_revision = verify_source_checkout(ROOT, registration_config, env)
    if git('remote', 'get-url', 'origin', capture=True).strip() not in (
            REPO_URL, 'https://github.com/seojelee9999/homelab-argocd.git'):
        raise RuntimeError('Unexpected GitOps origin; refusing to publish')
    if git('branch', '--show-current', capture=True).strip() != 'main':
        raise RuntimeError('GitOps checkout must be on main')
    if git('diff', '--cached', '--name-only', capture=True).strip():
        raise RuntimeError('Commit or unstage existing staged changes first')
    if git('diff', '--name-only', capture=True).strip():
        raise RuntimeError('Commit existing tracked changes first')
    if git('ls-files', '--others', '--exclude-standard', '--', *OWNED, capture=True).strip():
        raise RuntimeError('Untracked portfolio files exist; review and commit them first')
    git('fetch', 'origin', 'main')
    if git('rev-list', '--count', 'origin/main..HEAD', capture=True).strip() != '0':
        raise RuntimeError('Local unpushed commits exist; review them before running the installer')
    git('merge', '--ff-only', 'origin/main')
    for command in (
        'kubectl get nodes',
        'kubectl get storageclass longhorn-database -o name',
        'kubectl wait clustersecretstore/aws-parameter-store --for=condition=Ready --timeout=15s',
        'kubectl -n gateway-system wait gateway/tunnel-gateway --for=condition=Programmed --timeout=15s',
        'kubectl -n argocd get applicationset homelab-apps -o name',
    ):
        remote(command)
    registration = repo / 'apps/portfolio.json'
    if registration.is_symlink() or (repo / 'apps').is_symlink():
        raise RuntimeError('Refusing symlink registration destination')
    if registration.exists() and registration.read_bytes() != registration_source.read_bytes():
        raise RuntimeError('A different portfolio application is already registered')

    print('Creating missing SSM parameters; existing values will not be overwritten.', flush=True)
    remote('python3 - --admin-email ' + shlex.quote(args.admin_email),
           input=(ROOT / 'scripts/bootstrap_secrets.py').read_text())
    shutil.copyfile(registration_source, registration)
    git('add', '--', *OWNED)
    if git('diff', '--cached', '--name-only', capture=True).strip():
        git('commit', '-m', 'Register portfolio application')
        git('push', 'origin', 'HEAD:main')
    print('Waiting for Argo CD to reconcile portfolio (up to 10 minutes).', flush=True)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        result = subprocess.run([*ssh, args.host,
                                 'kubectl -n argocd get application portfolio -o json'],
                                capture_output=True, text=True)
        if result.returncode == 0:
            if application_is_ready(json.loads(result.stdout), registration_config, expected_revision):
                break
        print('Waiting for GitOps sync and healthy workloads...', flush=True)
        time.sleep(15)
    else:
        raise RuntimeError('Registration pushed, but deployment did not become healthy; inspect Argo CD')
    remote('kubectl -n portfolio get pods,pvc,externalsecrets,httproute')
    route = json.loads(remote('kubectl -n portfolio get httproute portfolio -o json', capture_output=True).stdout)
    parents = route.get('status', {}).get('parents', [])
    conditions = [condition for parent in parents
                  if parent.get('parentRef', {}).get('name') == 'tunnel-gateway'
                  for condition in parent.get('conditions', [])]
    for required in ('Accepted', 'ResolvedRefs'):
        if not any(c['type'] == required and c['status'] == 'True'
                   and c.get('observedGeneration') == route['metadata']['generation'] for c in conditions):
            raise RuntimeError(f'HTTPRoute condition {required} not confirmed for current generation')
    run([sys.executable, str(ROOT / 'scripts/smoke.py')])
    print('Deployment verified: https://akibaha.shop/portfolio/')
    print('Administrator:', args.admin_email)
    print('Read INITIAL_ADMIN_PASSWORD from SSM using README.md, then change it in your profile.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        sys.exit(1)
