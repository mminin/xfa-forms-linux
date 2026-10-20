#!/usr/bin/env python3
"""Offline regression tests for the source-release boundary and artifacts."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xfa-release-")
        self.root = Path(self.temp.name) / "public package"
        self.root.mkdir()
        self.output = Path(self.temp.name) / "assets"
        self.git("init", "-q")
        self.git("config", "user.name", "Release test")
        self.git("config", "user.email", "release@example.org")
        self.git("config", "commit.gpgsign", "false")
        (self.root / "scripts").mkdir()
        source = ROOT / "scripts/prepare-release.py"
        if not source.exists():
            source = ROOT / "public/scripts/prepare-release.py"
        shutil.copy2(source, self.root / "scripts/prepare-release.py")
        for name in ("README.md", "COPYING", "KNOWN_ISSUES.md", "TESTING.md"):
            (self.root / name).write_text(f"Fixture {name}\n")
        (self.root / "VERSION").write_text("0.1.0\n")
        (self.root / "RELEASE_NOTES.md").write_text("# Release 0.1.0\n")
        (self.root / ".gitignore").write_text("_work/\n")
        (self.root / "UPSTREAM").write_text("".join(
            f"{p} https://example.org/{p}.git {'a' * 40}\n" for p in ("quickjs", "zint", "poppler", "evince")))
        for project in ("poppler", "evince"):
            patches = self.root / "patches" / project
            patches.mkdir(parents=True)
            (patches / "0001-fixture.patch").write_text("Fixture patch\n")
        self.commit()

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args, **kwargs):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.STDOUT, **kwargs)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Fixture")

    def run_release(self, *args, script=None):
        return subprocess.run(["python3", str(script or self.root / "scripts/prepare-release.py"),
                               "--output", str(self.output), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)

    def assert_rejected(self, expected):
        result = self.run_release()
        self.assertNotEqual(result.returncode, 0, result.stdout.decode())
        self.assertIn(expected, result.stdout.decode())

    def test_reproducible_archive_and_checksums_exclude_ignored_files(self):
        ignored = self.root / "_work"
        ignored.mkdir()
        (ignored / "filled-private-document.pdf").write_bytes(b"%PDF\0private fixture")
        result = self.run_release()
        self.assertEqual(result.returncode, 0, result.stdout.decode())
        first = {p.name: p.read_bytes() for p in self.output.iterdir()}
        again = self.run_release()
        self.assertEqual(again.returncode, 0, again.stdout.decode())
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.output.iterdir()})
        for line in first["SHA256SUMS"].decode().splitlines():
            checksum, filename = line.split("  ", 1)
            self.assertEqual(checksum, hashlib.sha256(first[filename]).hexdigest())
        manifest = json.loads(first["release.json"])
        self.assertEqual(manifest["source_commit"], self.git("rev-parse", "HEAD").decode().strip())
        self.assertEqual(manifest["patches"], {"evince": 1, "poppler": 1})
        archive = gzip.decompress(first[manifest["archive"]])
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source.getmembers():
                self.assertTrue(member.name.startswith("xfa-forms-linux-0.1.0"))
                self.assertNotIn("_work", member.name)
                self.assertNotIn(".git/", member.name)
                self.assertTrue(member.isfile() or member.isdir())

    def test_check_writes_no_assets(self):
        result = self.run_release("--check")
        self.assertEqual(result.returncode, 0, result.stdout.decode())
        self.assertFalse(self.output.exists())

    def test_dirty_tracked_files_are_rejected(self):
        (self.root / "README.md").write_text("Uncommitted release changes\n")
        self.assert_rejected("working-tree changes")

    def test_untracked_files_are_rejected(self):
        (self.root / "answers.txt").write_text("Not a release input\n")
        self.assert_rejected("working-tree changes")

    def test_document_paths_are_rejected(self):
        (self.root / "tools").mkdir()
        (self.root / "tools/filled.pdf").write_text("Not source code\n")
        self.commit()
        self.assert_rejected("unexpected release path")

    def test_binary_source_is_rejected(self):
        (self.root / "scripts/hidden.py").write_bytes(b"binary\0data")
        self.commit()
        self.assert_rejected("binary release file")

    def test_symlinks_are_rejected(self):
        (self.root / "scripts/outside.sh").symlink_to("/etc/passwd")
        self.commit()
        self.assert_rejected("regular files only")

    def test_nested_private_repository_is_rejected(self):
        nested = self.root / "private/public/scripts"
        nested.mkdir(parents=True)
        script = nested / "prepare-release.py"
        shutil.copy2(self.root / "scripts/prepare-release.py", script)
        self.commit()
        result = self.run_release(script=script)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private source templates", result.stdout.decode())

    def test_version_cannot_escape_output_directory(self):
        (self.root / "VERSION").write_text("../../outside\n")
        self.commit()
        self.assert_rejected("plain release version")

    def test_patch_gaps_are_rejected(self):
        (self.root / "patches/poppler/0001-fixture.patch").rename(self.root / "patches/poppler/0002-fixture.patch")
        self.commit()
        self.assert_rejected("numbered consecutively")

    def test_existing_different_assets_are_preserved(self):
        self.output.mkdir()
        asset = self.output / "xfa-forms-linux-0.1.0.tar.gz"
        asset.write_bytes(b"Earlier candidate")
        self.assert_rejected("existing differing asset")
        self.assertEqual(asset.read_bytes(), b"Earlier candidate")
        self.assertEqual(list(self.output.iterdir()), [asset])

    def ubuntu_assets(self):
        assets = Path(self.temp.name) / "ubuntu-assets"
        assets.mkdir()
        info = {"version": "0.1.0", "source_commit": self.git("rev-parse", "HEAD").decode().strip(),
                "distribution": "Ubuntu 24.04", "architecture": "amd64",
                "package": "xfa-forms-linux_0.1.0-1_amd64.deb",
                "complete_source": "xfa-forms-linux-0.1.0-complete-source.tar.gz"}
        for key in ("package", "complete_source"):
            data = f"Fixture {key}\n".encode()
            (assets / info[key]).write_bytes(data)
            info[key + "_sha256"] = hashlib.sha256(data).hexdigest()
        (assets / "ubuntu-build.json").write_text(json.dumps(info))
        return assets, info

    def test_matching_ubuntu_assets_are_checksummed(self):
        assets, info = self.ubuntu_assets()
        result = self.run_release("--ubuntu-assets", str(assets))
        self.assertEqual(result.returncode, 0, result.stdout.decode())
        manifest = json.loads((self.output / "release.json").read_text())
        self.assertEqual(manifest["ubuntu"], info)
        for key in ("package", "complete_source"):
            self.assertEqual((self.output / info[key]).read_bytes(), (assets / info[key]).read_bytes())
            self.assertIn(info[key], (self.output / "SHA256SUMS").read_text())

    def test_ubuntu_assets_from_other_commit_are_rejected(self):
        assets, info = self.ubuntu_assets()
        info["source_commit"] = "0" * 40
        (assets / "ubuntu-build.json").write_text(json.dumps(info))
        result = self.run_release("--ubuntu-assets", str(assets))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must match this public commit", result.stdout.decode())
        self.assertFalse(self.output.exists())

    def test_revised_ubuntu_package_is_checksummed(self):
        assets, info = self.ubuntu_assets()
        revised = "xfa-forms-linux_0.1.0-2_amd64.deb"
        (assets / info["package"]).rename(assets / revised)
        info.update(package=revised, debian_revision="2")
        (assets / "ubuntu-build.json").write_text(json.dumps(info))
        result = self.run_release("--ubuntu-assets", str(assets))
        self.assertEqual(result.returncode, 0, result.stdout.decode())
        self.assertIn(revised, (self.output / "SHA256SUMS").read_text())

    def test_invalid_ubuntu_revision_is_rejected(self):
        assets, info = self.ubuntu_assets()
        for revision in ("../2", "0", "02", 2):
            info["debian_revision"] = revision
            (assets / "ubuntu-build.json").write_text(json.dumps(info))
            result = self.run_release("--ubuntu-assets", str(assets))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("revision must be", result.stdout.decode())
        self.assertFalse(self.output.exists())

    def test_modified_ubuntu_asset_is_rejected(self):
        assets, info = self.ubuntu_assets()
        (assets / info["package"]).write_bytes(b"modified package")
        result = self.run_release("--ubuntu-assets", str(assets))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stdout.decode())
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
