import copy
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

from install import application_is_ready, verify_source_checkout

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = json.loads((ROOT / 'gitops/apps/portfolio.json').read_text())
SOURCE_SHA = 'a' * 40
REGISTRATION_SHA = 'b' * 40


class GitOpsTests(unittest.TestCase):
    def setUp(self):
        self.application = {
            'spec': {'source': {'repoURL': REGISTRATION['repoURL'],
                                'path': 'deploy', 'targetRevision': 'main'}},
            'status': {'sync': {'status': 'Synced', 'revision': SOURCE_SHA},
                       'health': {'status': 'Healthy'}},
        }

    def test_health_uses_app_commit_not_registration_commit(self):
        self.assertTrue(application_is_ready(self.application, REGISTRATION, SOURCE_SHA))
        self.assertFalse(application_is_ready(self.application, REGISTRATION, REGISTRATION_SHA))

    def test_old_repo_or_path_is_not_reported_as_ready(self):
        for key, value in (('repoURL', 'https://github.com/seojelee9999/homelab-argocd.git'),
                           ('path', 'portfolio-resources'), ('targetRevision', 'other')):
            app = copy.deepcopy(self.application)
            app['spec']['source'][key] = value
            self.assertFalse(application_is_ready(app, REGISTRATION, SOURCE_SHA))

    def test_missing_or_degraded_app_is_not_ready(self):
        self.assertFalse(application_is_ready({}, REGISTRATION, SOURCE_SHA))
        self.application['status']['health']['status'] = 'Degraded'
        self.assertFalse(application_is_ready(self.application, REGISTRATION, SOURCE_SHA))

    def source_runner(self, *, dirty='', remote_sha=SOURCE_SHA):
        responses = {
            ('rev-parse', '--show-toplevel'): str(ROOT),
            ('remote', 'get-url', 'origin'): REGISTRATION['repoURL'],
            ('branch', '--show-current'): 'main',
            ('status', '--porcelain'): dirty,
            ('fetch', 'origin', 'main'): '',
            ('rev-parse', 'HEAD'): SOURCE_SHA,
            ('rev-parse', 'origin/main'): remote_sha,
        }

        def invoke(command, **kwargs):
            return types.SimpleNamespace(stdout=responses[tuple(command[3:])] + '\n')
        return invoke

    def test_requires_published_clean_source(self):
        with patch('install.run', side_effect=self.source_runner()):
            self.assertEqual(verify_source_checkout(ROOT, REGISTRATION, {}), SOURCE_SHA)
        with patch('install.run', side_effect=self.source_runner(dirty=' M deploy/bookstack.yaml')) as runner:
            with self.assertRaisesRegex(RuntimeError, 'publish all'):
                verify_source_checkout(ROOT, REGISTRATION, {})
            self.assertFalse(any('fetch' in call.args[0] for call in runner.call_args_list))
        with patch('install.run', side_effect=self.source_runner(remote_sha=REGISTRATION_SHA)):
            with self.assertRaisesRegex(RuntimeError, 'published origin/main'):
                verify_source_checkout(ROOT, REGISTRATION, {})

    def test_patch_adds_only_registration_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            subprocess.run(['git', 'init', '-q', temp], check=True)
            existing = repo / 'apps/schedule.json'
            existing.parent.mkdir()
            existing.write_text('{"existing": true}\n')
            subprocess.run(['git', '-C', temp, 'apply', str(ROOT / 'gitops/homelab-argocd.patch')], check=True)
            files = {p.relative_to(repo).as_posix() for p in repo.rglob('*')
                     if p.is_file() and '.git' not in p.relative_to(repo).parts}
            self.assertEqual(files, {'apps/schedule.json', 'apps/portfolio.json'})
            self.assertEqual(existing.read_text(), '{"existing": true}\n')
            self.assertEqual(json.loads((repo / 'apps/portfolio.json').read_text()), REGISTRATION)


if __name__ == '__main__':
    unittest.main()
