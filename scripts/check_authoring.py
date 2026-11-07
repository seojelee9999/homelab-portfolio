#!/usr/bin/env python3
"""Run rollback-only authoring checks inside the deployed BookStack runtime."""
import argparse
import io
import shlex
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='ubuntu@192.168.55.10')
    args = parser.parse_args()
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w') as tar:
        tar.add(ROOT / 'deploy/bootstrap/authoring.php', arcname='authoring.php')
        tar.add(ROOT / 'scripts/check_authoring.php', arcname='check_authoring.php')
        tar.add(ROOT / 'deploy/content', arcname='content')
        tar.add(ROOT / 'deploy/theme', arcname='theme')
    # Fixed command; no credentials or document content in output or shell arguments.
    shell = """
set -eu
check_dir=$(mktemp -d /tmp/portfolio-check.XXXXXX)
trap 'rm -rf "$check_dir"' EXIT
tar -xf - -C "$check_dir"
chmod -R a+rX "$check_dir"
php -l "$check_dir/authoring.php"
php -l "$check_dir/check_authoring.php"
php -l "$check_dir/theme/lang/ko/entities.php"
s6-setuidgid abc php "$check_dir/check_authoring.php"
"""
    command = 'kubectl -n portfolio exec -i deployment/portfolio-bookstack -- sh -c ' + shlex.quote(shell)
    subprocess.run(['ssh', '-F', '/dev/null', '-i', str(Path.home() / '.ssh/id_ed25519'),
                    '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                    args.host, command], input=archive.getvalue(), check=True)


if __name__ == '__main__':
    main()
