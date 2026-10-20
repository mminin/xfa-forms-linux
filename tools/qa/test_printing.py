#!/usr/bin/env python3
"""Linux desktop printing regressions; run with scripts/test-printing.sh.

Uses synthetic documents, the real print dialogs and preview subprocesses.
Only Print to File is selected. Requires pdfinfo/pdftotext and a private display.
"""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
PREFIX = ROOT / "_install"
OUT = ROOT / "_work/qa/printing-regressions"


def pdf(objects):
    data = b"%PDF-1.7\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets[1:])
    return data + f"trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{xref}\n%%EOF\n".encode()


def stream(value):
    return f"<< /Length {len(value)} >>\nstream\n".encode() + value + b"\nendstream"


def helpers(token):
    result = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args = (proc / "cmdline").read_bytes().split(b"\0")
            if not args or Path(os.fsdecode(args[0])).name != "evince-previewer":
                continue
            if f"XFA_PRINT_TEST_TOKEN={token}".encode() in (proc / "environ").read_bytes().split(b"\0"):
                result.append((proc, args))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return result


class Printing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True, exist_ok=True)
        cls.ordinary = OUT / "ordinary printer's fixture.pdf"
        cls.ordinary.write_bytes(pdf([
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
            *[f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents {n} 0 R >>".encode() for n in (6, 7)],
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            *[stream(f"BT /F1 24 Tf 72 700 Td (Printing regression page {n}) Tj ET".encode()) for n in (1, 2)],
        ]))
        cls.xfa = OUT / "XFA printer's fixture.pdf"
        xdp = b'''<xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">
<template xmlns="http://www.xfa.org/schema/xfa-template/3.3/">
<subform name="form1" layout="tb">
<pageSet><pageArea name="Page1"><contentArea x="1in" y="1in" w="6in" h="9in"/>
<medium short="8.5in" long="11in"/></pageArea></pageSet>
<field name="answer" w="4in" h="0.5in"><ui><textEdit/></ui><value><text>XFA printed answer</text></value></field>
</subform></template></xdp:xdp>'''
        cls.xfa.write_bytes(pdf([
            b"<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [] /XFA 4 0 R >> /NeedsRendering true >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>", stream(xdp),
        ]))

    def inspect_pdf(self, path, xfa):
        info = subprocess.check_output(["pdfinfo", str(path)], text=True, stderr=subprocess.STDOUT)
        pages = [s.split(":", 1)[1].strip() for s in info.splitlines() if s.startswith("Pages:")]
        self.assertEqual(pages, ["1" if xfa else "2"])
        text = subprocess.check_output(["pdftotext", str(path), "-"], text=True)
        for expected in (["XFA printed answer"] if xfa else ["Printing regression page 1", "Printing regression page 2"]):
            self.assertIn(expected, text)

    def preview(self, token, xfa, name):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            for proc, args in helpers(token):
                self.assertEqual((proc / "exe").resolve(), PREFIX / "bin/evince-previewer")
                try:
                    maps = (proc / "maps").read_text()
                except FileNotFoundError:
                    continue
                if str(PREFIX / "lib/x86_64-linux-gnu/evince/6/backends/libpdfdocument.so") not in maps:
                    continue
                source = Path(os.fsdecode([a for a in args if a][-1]))
                if source.exists():
                    self.inspect_pdf(source, xfa)
                    shutil.copyfile(source, OUT / f"{name}-preview.pdf")
                    return
            time.sleep(0.1)
        self.fail("Matching local previewer did not load its PDF backend")

    def cleanup_helpers(self, token):
        for proc, args in helpers(token):
            os.kill(int(proc.name), signal.SIGTERM)
            for arg in args[1:]:
                path = Path(os.fsdecode(arg))
                if path.is_absolute() and (path.parent == Path("/tmp") or path.parent == OUT):
                    path.unlink(missing_ok=True)

    def run_case(self, action, export, xfa):
        name = f"{'xfa' if xfa else 'ordinary'}-{'export' if export else 'direct'}-{action}"
        token = uuid.uuid4().hex
        env = dict(os.environ, XFA_PRINT_TEST_TOKEN=token, EV_PRINT="export" if export else "print")
        output = OUT / f"{name}.pdf"
        output.unlink(missing_ok=True)
        try:
            with (OUT / f"{name}.log").open("w") as log:
                subprocess.run([str(ROOT / "_work/tests/check-printing"), action,
                                str(self.xfa if xfa else self.ordinary), str(output)],
                               env=env, stdout=log, stderr=log, check=True, timeout=35)
            if action == "preview":
                self.preview(token, xfa, name)
                self.assertFalse(output.exists())
            elif action == "file":
                deadline = time.monotonic() + 5
                while not output.exists() and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.inspect_pdf(output, xfa)
            else:
                self.assertFalse(output.exists())
                self.assertFalse(helpers(token))
        finally:
            self.cleanup_helpers(token)

    def test_print_dialogs(self):
        for xfa in (False, True):
            for export in (False, True):
                for action in ("preview", "file", "cancel"):
                    with self.subTest(xfa=xfa, export=export, action=action):
                        self.run_case(action, export, xfa)

    def test_launcher_uses_matching_preview_helper(self):
        # Start with the system PATH: the launcher must select its own helpers.
        for xfa in (False, True):
            with self.subTest(xfa=xfa):
                token = uuid.uuid4().hex
                name = f"launcher-{'xfa' if xfa else 'ordinary'}"
                source = OUT / f"{name} printer's preview.pdf"
                # Preview receives the already rendered print PDF from GTK.
                if xfa:
                    subprocess.run([str(PREFIX / "bin/pdfxfa"), "-print", str(self.xfa), str(source)],
                                   check=True, stdout=subprocess.DEVNULL)
                else:
                    shutil.copyfile(self.ordinary, source)
                env = dict(os.environ, PATH="/usr/bin:/bin", XFA_PRINT_TEST_TOKEN=token)
                settings = OUT / f"{name} printer's settings.ini"
                settings.write_text("[Print Settings]\nprinter=Print to File\n")
                try:
                    with (OUT / f"{name}.log").open("w") as log:
                        subprocess.run([str(ROOT / "scripts/run-evince.sh"), "--preview", "--unlink-tempfile",
                                        "--print-settings", str(settings), str(source)],
                                       env=env, stdout=log, stderr=log, check=True, timeout=10)
                    self.preview(token, xfa, name)
                finally:
                    self.cleanup_helpers(token)


if __name__ == "__main__":
    unittest.main(verbosity=2)
