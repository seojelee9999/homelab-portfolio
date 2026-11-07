#!/usr/bin/env python3
"""Produce only the Argo CD registration patch; manifests stay in this repo."""
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = {'apps/portfolio.json': ROOT / 'gitops/apps/portfolio.json'}
    chunks = []
    for target, source in sorted(files.items()):
        chunks.extend([f'diff --git a/{target} b/{target}\n', 'new file mode 100644\n'])
        chunks.extend(difflib.unified_diff([], source.read_text().splitlines(keepends=True),
                                           fromfile='/dev/null', tofile='b/' + target))
    output = ROOT / 'gitops/homelab-argocd.patch'
    output.write_text(''.join(chunks))
    print(f'Prepared {output} ({len(files)} files, no secrets)')


if __name__ == '__main__':
    main()
