#!/usr/bin/env python3
"""Offline complete-source and package-build workspace regressions."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/build-ubuntu-package.py"
if not BUILDER.exists():
    BUILDER = ROOT / "public/scripts/build-ubuntu-package.py"
spec = importlib.util.spec_from_file_location("ubuntu_package", BUILDER)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class UbuntuSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xfa-ubuntu-source-")
        self.root = Path(self.temp.name)
        self.files = {"VERSION": (0o644, b"0.1.0\n"), "scripts/build.sh": (0o755, b"#!/bin/sh\nexit 0\n")}
        self.info = {
            "project": "xfa-forms-linux", "version": "0.1.0", "source_commit": "a" * 40,
            "source_date_epoch": 1700000000,
            "upstream": {p: {"tree": "b" * 40} for p in builder.PROJECTS},
            "files": {p: {"mode": mode, "sha256": hashlib.sha256(data).hexdigest()} for p, (mode, data) in self.files.items()},
        }
        builder.write_sources(self.root, self.files, self.info)

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_source_manifest_roundtrip(self):
        self.assertEqual(builder.verify_sources(self.root, self.info), self.files)
        first, second = self.root / "first.tar.gz", self.root / "second.tar.gz"
        builder.complete_source(first, self.files, self.info)
        builder.complete_source(second, self.files, self.info)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        extracted = self.root / "extracted"
        with tarfile.open(first) as archive:
            archive.extractall(extracted, filter="data")
        source = extracted / "xfa-forms-linux-0.1.0"
        info = json.loads((source / "SOURCE_INFO.json").read_text())
        self.assertEqual(builder.verify_sources(source, info), self.files)
        self.assertFalse((source / ".git").exists())

    def test_modified_source_is_rejected(self):
        (self.root / "scripts/build.sh").write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            builder.verify_sources(self.root, self.info)

    def test_source_paths_cannot_escape(self):
        self.info["files"]["../outside"] = self.info["files"]["VERSION"]
        with self.assertRaisesRegex(ValueError, "unsafe source path"):
            builder.verify_sources(self.root, self.info)

    def test_source_symlink_is_rejected(self):
        path = self.root / "VERSION"
        path.unlink()
        path.symlink_to("/etc/passwd")
        with self.assertRaisesRegex(ValueError, "source symlink"):
            builder.verify_sources(self.root, self.info)

    def test_upstream_archive_symlink_is_rejected(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as archive:
            member = tarfile.TarInfo("outside")
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
            archive.addfile(member)
        with self.assertRaisesRegex(ValueError, "regular files"):
            builder.archive_files(data.getvalue())

    def test_restage_preserves_build_outputs(self):
        build = self.root / "_build/cache"
        build.parent.mkdir()
        build.write_text("cached build output\n")
        builder.write_sources(self.root, self.files, self.info)
        self.assertEqual(build.read_text(), "cached build output\n")

if __name__ == "__main__":
    unittest.main(verbosity=2)
