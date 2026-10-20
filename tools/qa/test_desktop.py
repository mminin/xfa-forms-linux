#!/usr/bin/env python3
"""Installed Ubuntu package: service discovery, registration and reopen.

Run on a private display. Starts a fresh bus with standard system data paths,
before the launcher's private environment exists. Needs dbus-run-session/gdbus.
"""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from test_core import pdf as xfa_pdf, template
from test_printing import pdf, stream

SERVICE = "org.gnome.Evince.XFA.Daemon"
OBJECT_PATH = "/org/gnome/Evince/XFA/Daemon"
LAUNCHER = os.environ.get("XFA_TEST_LAUNCHER", "/usr/bin/xfa-forms-linux")


def call(destination, path, method, *args):
    result = subprocess.run(["gdbus", "call", "--session", "--dest", destination,
                             "--object-path", path, "--method", method, *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    if result.returncode:
        raise RuntimeError(result.stderr.decode())
    return ast.literal_eval(result.stdout.decode())


class Desktop(unittest.TestCase):
    def test_00_service_is_discoverable_before_launch(self):
        names, = call("org.freedesktop.DBus", "/org/freedesktop/DBus",
                      "org.freedesktop.DBus.ListActivatableNames")
        self.assertIn(SERVICE, names)

    def check_registration(self, data):
        with tempfile.TemporaryDirectory(prefix="xfa-desktop-document-") as temporary:
            source = Path(temporary) / "test form's document.pdf"
            source.write_bytes(data)
            # GIO leaves apostrophes unescaped; pathlib.as_uri() does not.
            # Query the same URI spelling that the viewer registers.
            info = subprocess.check_output(["gio", "info", "-a", "standard::type", str(source)],
                                           env=dict(os.environ, LC_ALL="C"), timeout=5).decode()
            uri = next(line[5:] for line in info.splitlines() if line.startswith("uri: "))
            log = Path(temporary) / "viewer.log"
            with log.open("w") as output:
                process = subprocess.Popen([LAUNCHER, str(source)], stdout=output, stderr=output)
                try:
                    deadline = time.monotonic() + 15
                    owner = ""
                    while time.monotonic() < deadline:
                        self.assertIsNone(process.poll(), log.read_text())
                        owner, = call(SERVICE, OBJECT_PATH,
                                      "org.gnome.Evince.Daemon.FindDocument", uri, "false")
                        if owner:
                            break
                        time.sleep(.1)
                    self.assertTrue(owner, "Document was never registered: " + log.read_text())
                    # Reopening must route to the registered viewer and exit.
                    reopened = subprocess.run([LAUNCHER, str(source)], stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, timeout=10)
                    self.assertEqual(reopened.returncode, 0, reopened.stderr.decode())
                    same_owner, = call(SERVICE, OBJECT_PATH,
                                           "org.gnome.Evince.Daemon.FindDocument", uri, "false")
                    self.assertEqual(same_owner, owner)
                    self.assertIsNone(process.poll())
                    self.assertNotIn("Error registering document", log.read_text())
                    self.assertNotIn("Gtk-WARNING", log.read_text())
                finally:
                    process.terminate()
                    process.wait(timeout=5)

    def test_ordinary_registration_and_reopen(self):
        self.check_registration(pdf([
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
            stream(b"0 0 20 20 re f"),
        ]))

    def test_xfa_registration_and_reopen(self):
        self.check_registration(xfa_pdf(template()))


if __name__ == "__main__":
    if "--inside-session" in sys.argv:
        sys.argv.remove("--inside-session")
        unittest.main(verbosity=2)
    else:
        with tempfile.TemporaryDirectory(prefix="xfa-desktop-session-") as temporary:
            env = os.environ.copy()
            # Setting these only in the viewer was the original packaging bug.
            for name in ("DBUS_SESSION_BUS_ADDRESS", "LD_LIBRARY_PATH", "EV_BACKENDS_DIR",
                         "GSETTINGS_SCHEMA_DIR"):
                env.pop(name, None)
            env.update(XDG_DATA_DIRS="/usr/local/share:/usr/share",
                       XDG_CONFIG_HOME=temporary + "/config", XDG_DATA_HOME=temporary + "/data",
                       XDG_CACHE_HOME=temporary + "/cache", GSETTINGS_BACKEND="memory", GTK_A11Y="none")
            sys.exit(subprocess.run(["dbus-run-session", "--", sys.executable, str(Path(__file__).resolve()),
                                     "--inside-session", *sys.argv[1:]], env=env).returncode)
