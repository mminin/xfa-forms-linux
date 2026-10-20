#!/usr/bin/env python3
"""Offline package regressions: interrupted bootstrap and verified downloads."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xfa-package-')
        self.base = Path(self.temp.name)
        self.package = self.base / 'package with spaces'
        (self.package / 'scripts').mkdir(parents=True)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.env = os.environ.copy()
        self.env['PATH'] = str(self.bin) + os.pathsep + self.env['PATH']

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *args, cwd=None):
        return subprocess.run(args, cwd=cwd or self.package, env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)

    def script(self, name):
        source = ROOT / 'scripts' / name
        if not source.exists():
            source = ROOT / 'public/scripts' / name
        shutil.copy2(source, self.package / 'scripts' / name)
        return str(self.package / 'scripts' / name)

    def make_upstream(self):
        cache = self.base / 'upstream-cache'
        subprocess.run(['git', 'init', '-q', str(cache)], check=True)
        (cache / 'source.txt').write_text('pinned source\n')
        subprocess.run(['git', '-C', str(cache), 'add', 'source.txt'], check=True)
        subprocess.run(['git', '-C', str(cache), '-c', 'user.name=QA', '-c', 'user.email=qa@example.org',
                        'commit', '-qm', 'fixture'], check=True)
        revision = subprocess.check_output(['git', '-C', str(cache), 'rev-parse', 'HEAD']).decode().strip()
        (self.package / 'UPSTREAM').write_text(f'quickjs {cache} {revision}\n')
        return revision

    def test_interrupted_fetch_is_retried(self):
        script = self.script('bootstrap.sh')
        revision = self.make_upstream()
        real_git = shutil.which('git')
        marker = self.base / 'fetch-attempted'
        wrapper = self.bin / 'git'
        wrapper.write_text('#!/bin/sh\n'
                           'if [ "${3:-}" = fetch ] && [ ! -e "$QA_FETCH_MARKER" ]; then\n'
                           '    touch "$QA_FETCH_MARKER"; exit 77\nfi\n'
                           'exec "$QA_REAL_GIT" "$@"\n')
        wrapper.chmod(0o755)
        self.env.update(QA_FETCH_MARKER=str(marker), QA_REAL_GIT=real_git)
        first = self.command(script)
        self.assertNotEqual(first.returncode, 0, first.stdout.decode())
        second = self.command(script)
        self.assertEqual(second.returncode, 0, second.stdout.decode())
        head = self.command('git', '-C', str(self.package / 'upstream/quickjs'), 'rev-parse', 'HEAD')
        self.assertEqual(head.returncode, 0, head.stdout.decode())
        self.assertEqual(head.stdout.decode().strip(), revision)

    def test_incomplete_patch_application_is_not_success(self):
        script = self.script('bootstrap.sh')
        self.make_upstream()
        patches = self.package / 'patches/quickjs'
        patches.mkdir(parents=True)
        (patches / '0001.patch').write_text('broken patch\n')
        self.assertNotEqual(self.command(script).returncode, 0)
        again = self.command(script)
        self.assertNotEqual(again.returncode, 0, again.stdout.decode())

    def test_bootstrap_is_idempotent(self):
        script = self.script('bootstrap.sh')
        self.make_upstream()
        self.assertEqual(self.command(script).returncode, 0)
        source = self.package / 'upstream/quickjs/source.txt'
        source.write_text('local developer edit\n')
        again = self.command(script)
        self.assertEqual(again.returncode, 0, again.stdout.decode())
        self.assertEqual(source.read_text(), 'local developer edit\n')

    def download_fixture(self, body, status=0):
        script = self.script('fetch-corpus.sh')
        (self.package / 'corpus').mkdir(exist_ok=True)
        payload = b'verified sample'
        checksum = hashlib.sha256(payload).hexdigest()
        (self.package / 'corpus/forms.tsv').write_text(
            'file\tdepartment\ttitle\tpage\tpdf_url\tsha256\tkind\tneeds\n'
            f'form.pdf\tQA\tFixture\thttps://example.org/\thttps://example.org/form.pdf\t{checksum}\tdynamic\t-\n')
        curl = self.bin / 'curl'
        curl.write_text('#!/bin/sh\nprintf "%s" "$QA_DOWNLOAD_BODY" > "$3"\nexit "$QA_DOWNLOAD_STATUS"\n')
        curl.chmod(0o755)
        self.env.update(QA_DOWNLOAD_BODY=body, QA_DOWNLOAD_STATUS=str(status))
        return script

    def test_download_failure_is_not_success(self):
        script = self.download_fixture('partial bytes', 22)
        result = self.command(script)
        self.assertNotEqual(result.returncode, 0, result.stdout.decode())
        self.assertFalse((self.package / 'corpus/files/form.pdf').exists())

    def test_checksum_failure_is_not_success(self):
        script = self.download_fixture('unexpected version')
        result = self.command(script)
        self.assertNotEqual(result.returncode, 0, result.stdout.decode())
        self.assertFalse((self.package / 'corpus/files/form.pdf').exists())

    def test_verified_download_and_cache(self):
        script = self.download_fixture('verified sample')
        first = self.command(script)
        self.assertEqual(first.returncode, 0, first.stdout.decode())
        path = self.package / 'corpus/files/form.pdf'
        self.assertEqual(path.read_bytes(), b'verified sample')
        self.env.update(QA_DOWNLOAD_BODY='partial bytes', QA_DOWNLOAD_STATUS='22')
        again = self.command(script)
        self.assertEqual(again.returncode, 0, again.stdout.decode())
        self.assertEqual(path.read_bytes(), b'verified sample')


if __name__ == '__main__':
    unittest.main(verbosity=2)
