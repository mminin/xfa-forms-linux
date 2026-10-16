#!/usr/bin/env python3
"""Register the locally built viewer; optionally use it for PDF double-clicks."""
import argparse
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--applications-dir', type=Path,
                    default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'applications')
parser.add_argument('--make-default', action='store_true')
args = parser.parse_args()
launcher = root / 'scripts/run-evince.sh'
if not (root / '_install/bin/evince').is_file():
    parser.error('Build the viewer with scripts/build.sh first.')
args.applications_dir.mkdir(parents=True, exist_ok=True)
entry = args.applications_dir / 'org.gnome.Evince.Devel.desktop'
command = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
entry.write_text(f'''[Desktop Entry]
Type=Application
Name=Document Viewer (XFA)
Comment=Local Evince build with interactive XFA forms
Exec="{command}" %U
TryExec={launcher}
Icon={root}/_install/share/icons/hicolor/scalable/apps/org.gnome.Evince.Devel.svg
Terminal=false
DBusActivatable=false
MimeType=application/pdf;
Categories=GNOME;GTK;Office;Viewer;
''')
subprocess.run(['desktop-file-validate', str(entry)], check=True)
subprocess.run(['update-desktop-database', str(args.applications_dir)], check=True)
if args.make_default:
    subprocess.run(['gio', 'mime', 'application/pdf', entry.name], check=True)
print(f'Registered {entry}')
