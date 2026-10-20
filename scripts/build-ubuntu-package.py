#!/usr/bin/env python3
"""Build an isolated Ubuntu 24.04 amd64 package and its complete source archive.

Requires the normal build dependencies, bubblewrap, dpkg-dev and binutils.
Run bootstrap first in a public Git checkout, or use a complete source archive.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path("/opt/xfa-forms-linux")
PACKAGE = "xfa-forms-linux"
PROJECTS = ("quickjs", "zint", "poppler", "evince")


def run(args, **kwargs):
    return subprocess.check_output([str(a) for a in args], **kwargs)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts or str(path) != name:
        raise ValueError(f"unsafe source path: {name}")
    return path


def archive_files(data, prefix=""):
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            if member.isdir():
                continue
            safe_path(member.name)
            if not member.isfile():
                raise ValueError(f"source archive must contain regular files: {member.name}")
            files[prefix + member.name] = (member.mode & 0o755, archive.extractfile(member).read())
    return files


def verify_sources(root, info):
    if info.get("project") != PACKAGE or set(info.get("upstream", {})) != set(PROJECTS):
        raise ValueError("invalid complete-source manifest")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", info.get("version", "")):
        raise ValueError("invalid source version")
    files = {}
    for name, entry in info["files"].items():
        path = root.joinpath(*safe_path(name).parts)
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"source symlink or escaped path: {name}")
        data = path.read_bytes()
        if digest(data) != entry["sha256"]:
            raise ValueError(f"source checksum mismatch: {name}")
        if entry["mode"] not in (0o644, 0o755):
            raise ValueError(f"invalid source permissions: {name}")
        files[name] = (entry["mode"], data)
    if files["VERSION"][1].decode().strip() != info["version"]:
        raise ValueError("source VERSION does not match manifest")
    return files


def source_inputs():
    manifest = ROOT / "SOURCE_INFO.json"
    if manifest.exists():
        info = json.loads(manifest.read_text())
        return info, verify_sources(ROOT, info)
    spec = importlib.util.spec_from_file_location("release", ROOT / "scripts/prepare-release.py")
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    version, _, _, upstream = release.inspect()
    files = archive_files(release.git("archive", "HEAD"))
    for name in PROJECTS:
        directory = ROOT / "upstream" / name
        def git(*args):
            return run(["git", "-C", directory, *args])
        head = git("rev-parse", "HEAD").decode().strip()
        recorded = git("config", "--get", "xfa.bootstrap-head").decode().strip()
        lines = upstream[name]["commit"] + "\n"
        for patch in sorted((ROOT / "patches" / name).glob("*.patch")):
            lines += f"{digest(patch.read_bytes())}  {patch.name}\n"
        fingerprint = git("config", "--get", "xfa.bootstrap-source").decode().strip()
        if head != recorded or fingerprint != digest(lines.encode()) or git("status", "--porcelain").strip():
            raise ValueError(f"upstream/{name} differs from the completed bootstrap; use fresh sources")
        upstream[name]["tree"] = git("rev-parse", "HEAD^{tree}").decode().strip()
        files.update(archive_files(git("archive", "HEAD"), f"upstream/{name}/"))
    info = {
        "project": PACKAGE, "version": version,
        "source_commit": release.git("rev-parse", "HEAD").decode().strip(),
        "source_date_epoch": int(release.git("show", "-s", "--format=%ct", "HEAD")),
        "upstream": upstream,
        "files": {p: {"mode": mode, "sha256": digest(data)} for p, (mode, data) in sorted(files.items())},
    }
    return info, files


def write_sources(directory, files, info):
    previous = directory / "SOURCE_INFO.json"
    if previous.exists():
        old = json.loads(previous.read_text())
        for name in old["files"].keys() - files.keys():
            directory.joinpath(*safe_path(name).parts).unlink(missing_ok=True)
    directory.mkdir(parents=True, exist_ok=True)
    for name, (mode, data) in files.items():
        path = directory.joinpath(*safe_path(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
        path.chmod(mode)
    previous.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")


def complete_source(output, files, info):
    entries = dict(files)
    entries["SOURCE_INFO.json"] = (0o644, (json.dumps(info, indent=2, sort_keys=True) + "\n").encode())
    entries["BUILD_COMPLETE_SOURCE.md"] = (0o644, b"""# Building the complete source archive

All four upstream source trees are included, with the released patches applied.
Do not run bootstrap.sh: no source fetch is needed.

Install the Ubuntu build dependencies with scripts/install-build-deps.sh.
For a local viewer, run scripts/build.sh and scripts/run-evince.sh.
To rebuild the .deb, install bubblewrap dpkg-dev binutils and run:

    python3 scripts/build-ubuntu-package.py

This validates SOURCE_INFO.json and compiles using an isolated /opt prefix.
The optional QuickJS test262 corpus is not included or needed for the build.
""")
    with output.open("wb") as target:
        with gzip.GzipFile(filename="", fileobj=target, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as archive:
                for name, (mode, data) in sorted(entries.items()):
                    member = tarfile.TarInfo(f"{PACKAGE}-{info['version']}/{name}")
                    member.mode = mode
                    member.size = len(data)
                    member.mtime = info["source_date_epoch"]
                    archive.addfile(member, io.BytesIO(data))


def launcher(target):
    return f'''#!/bin/sh
PREFIX={PREFIX}
export PATH="$PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib/x86_64-linux-gnu:${{LD_LIBRARY_PATH:-}}"
export XDG_DATA_DIRS="$PREFIX/share:${{XDG_DATA_DIRS:-/usr/local/share:/usr/share}}"
export GSETTINGS_SCHEMA_DIR="$PREFIX/share/glib-2.0/schemas"
export EV_BACKENDS_DIR="$PREFIX/lib/x86_64-linux-gnu/evince/6/backends"
exec "$PREFIX/{target}" "$@"
'''


def put(root, name, data, mode=0o644):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    path.chmod(mode)


def assemble(prefix, payload, files, info):
    installed = payload / str(PREFIX).lstrip("/")
    installed.mkdir(parents=True)
    for name in ("evince", "evince-previewer", "pdfxfa"):
        destination = installed / "bin" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prefix / "bin" / name, destination)
    (installed / "libexec").mkdir()
    shutil.copy2(prefix / "libexec/evinced", installed / "libexec/evinced")
    for pattern in ("lib/libpoppler.so*", "lib/libpoppler-glib.so*",
                    "lib/x86_64-linux-gnu/libevdocument-4.0.so*", "lib/x86_64-linux-gnu/libevview-4.0.so*"):
        for source in prefix.glob(pattern):
            destination = installed / source.relative_to(prefix)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=False)
    shutil.copytree(prefix / "lib/x86_64-linux-gnu/evince", installed / "lib/x86_64-linux-gnu/evince")
    for name in ("glib-2.0", "icons", "locale"):
        shutil.copytree(prefix / "share" / name, installed / "share" / name)
    put(payload, "usr/bin/xfa-forms-linux", launcher("bin/evince"), 0o755)
    put(payload, "usr/bin/xfa-pdf", launcher("bin/pdfxfa"), 0o755)
    put(installed, "bin/xfa-evinced", launcher("libexec/evinced"), 0o755)
    service = installed / "share/dbus-1/services/org.gnome.Evince.XFA.Daemon.service"
    service.parent.mkdir(parents=True)
    shutil.copy2(prefix / "share/dbus-1/services/org.gnome.Evince.XFA.Daemon.service", service)
    service.write_text(re.sub(r"^Exec=.*$", f"Exec={PREFIX}/bin/xfa-evinced", service.read_text(), flags=re.M))
    put(payload, "usr/share/applications/org.gnome.Evince.XFA.desktop", '''[Desktop Entry]
Type=Application
Name=Document Viewer (XFA)
Comment=Open and fill dynamic XFA PDF forms
Exec=xfa-forms-linux %U
TryExec=xfa-forms-linux
Icon=org.gnome.Evince.XFA
Terminal=false
DBusActivatable=false
MimeType=application/pdf;
Categories=GNOME;GTK;Office;Viewer;
''')
    icon = payload / "usr/share/icons/hicolor/scalable/apps/org.gnome.Evince.XFA.svg"
    icon.parent.mkdir(parents=True)
    shutil.copy2(prefix / "share/icons/hicolor/scalable/apps/org.gnome.Evince.XFA.svg", icon)
    doc = payload / "usr/share/doc" / PACKAGE
    doc.mkdir(parents=True)
    for name in ("README.md", "RELEASE_NOTES.md", "KNOWN_ISSUES.md", "TESTING.md", "PR_PLAN.md", "UPSTREAM", "VERSION"):
        (doc / name).write_bytes(files[name][1])
    for project, source, target in (("poppler", "COPYING", "Poppler-COPYING"),
                                    ("evince", "COPYING", "Evince-COPYING"),
                                    ("quickjs", "LICENSE", "QuickJS-LICENSE"),
                                    ("zint", "LICENSE", "Zint-LICENSE"),
                                    ("zint", "backend/common.h", "Zint-BSD-notice.h")):
        (doc / target).write_bytes(files[f"upstream/{project}/{source}"][1])
    (doc / "copyright").write_bytes(b"XFA forms in Evince: GPL-2.0-or-later.\n"
                                    b"See the accompanying upstream license notices and complete source archive.\n\n" + files["COPYING"][1])
    elf = []
    for path in sorted(payload.rglob("*")):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as source:
                if source.read(4) == b"\x7fELF":
                    subprocess.run(["strip", "--strip-unneeded", str(path)], check=True)
                    elf.append(path)
    return elf


def package(payload, elf, output, info):
    control_dir = payload / "DEBIAN"
    control_dir.mkdir()
    version = info["version"] + "-1"
    with tempfile.TemporaryDirectory(prefix="dependency-", dir=output) as temporary:
        temporary = Path(temporary)
        (temporary / "debian").mkdir()
        (temporary / "debian/control").write_text(f"Source: {PACKAGE}\n\nPackage: {PACKAGE}\nArchitecture: amd64\n")
        shlibs = temporary / "shlibs.local"
        lines = []
        for path in elf:
            dynamic = run(["readelf", "-d", path]).decode()
            match = re.search(r"\(SONAME\).*\[([^]]+)\]", dynamic)
            if match:
                name = re.fullmatch(r"(.+)\.so\.(\d+)", match[1])
                if name:
                    lines.append(f"{name[1]} {name[2]} {PACKAGE} (= {version})\n")
        shlibs.write_text("".join(lines))
        library = payload / str(PREFIX).lstrip("/") / "lib"
        args = ["dpkg-shlibdeps", "-O", f"-L{shlibs}", f"-x{PACKAGE}", f"-l{library}", f"-l{library / 'x86_64-linux-gnu'}"]
        result = run([*args, *[f"-e{p}" for p in elf]], cwd=temporary).decode()
    dependencies = result.strip().removeprefix("shlibs:Depends=")
    dependencies += ", shared-mime-info, gsettings-desktop-schemas, desktop-file-utils, adwaita-icon-theme, poppler-data"
    size = math.ceil(sum(p.stat().st_size for p in payload.rglob("*") if p.is_file() and not p.is_symlink()) / 1024)
    (control_dir / "control").write_text(f'''Package: {PACKAGE}
Version: {version}
Architecture: amd64
Maintainer: mminin <mminin2010@gmail.com>
Section: graphics
Priority: optional
Depends: {dependencies}
Recommends: fonts-dejavu-core, fonts-liberation2
Suggests: fonts-noto-cjk
Installed-Size: {size}
Description: Experimental PDF viewer with dynamic XFA form support
 Patched Evince and Poppler with local XFA layout, scripting, editing,
 saved form restoration and printing. Installs private libraries under
 /opt/xfa-forms-linux and a Document Viewer (XFA) launcher.
''')
    (control_dir / "md5sums").write_text("".join(
        f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.relative_to(payload)}\n"
        for p in sorted(payload.rglob("*")) if p.is_file() and not p.is_symlink() and control_dir not in p.parents))
    epoch = info["source_date_epoch"]
    for path in [payload, *payload.rglob("*")]:
        os.utime(path, (epoch, epoch), follow_symlinks=False)
    target = output / f"{PACKAGE}_{version}_amd64.deb"
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", "--threads-max=1", "-Zxz", "-z9", str(payload), str(target)],
                   check=True, env=env)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "_work/ubuntu-package")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--check-source", action="store_true", help="verify complete source inputs without building")
    args = parser.parse_args()
    try:
        info, files = source_inputs()
        if args.check_source:
            print(f"Verified {len(files)} source files for {info['version']} ({info['source_commit']})")
            return
        if args.jobs < 1:
            raise ValueError("--jobs must be positive")
        os_release = Path("/etc/os-release").read_text()
        if 'ID=ubuntu\n' not in os_release or 'VERSION_ID="24.04"' not in os_release or run(["dpkg", "--print-architecture"]).strip() != b"amd64":
            raise ValueError("build this package on Ubuntu 24.04 amd64")
        work = args.work_dir.resolve()
        if work == ROOT or ROOT.is_relative_to(work):
            raise ValueError("work directory must not contain the source checkout")
        work.mkdir(parents=True, exist_ok=True)
        source = work / "source"
        write_sources(source, files, info)
        prefix = work / "prefix"
        prefix.mkdir(exist_ok=True)
        output = work / "assets"
        output.mkdir(exist_ok=True)
        command = ["bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--tmpfs", "/opt", "--bind", str(prefix), str(PREFIX),
                   "--tmpfs", "/tmp", "--bind", str(source), "/tmp/xfa-build", "--proc", "/proc", "--dev", "/dev",
                   "--unshare-pid", "--unshare-net", "--chdir", "/tmp/xfa-build",
                   "--setenv", "PATH", "/usr/bin:/bin", "--unsetenv", "LD_LIBRARY_PATH", "--unsetenv", "PKG_CONFIG_PATH",
                   "--unsetenv", "CMAKE_PREFIX_PATH", "--setenv", "XFA_INSTALL_PREFIX", str(PREFIX),
                   "--setenv", "XFA_APPLICATION_ID", "org.gnome.Evince.XFA",
                   "--setenv", "JOBS", str(args.jobs), "--setenv", "XDG_CACHE_HOME", "/tmp/xfa-build/_work/cache",
                   "/bin/sh", "scripts/build.sh"]
        subprocess.run(command, check=True)
        with tempfile.TemporaryDirectory(prefix="payload-", dir=work) as temporary:
            payload = Path(temporary)
            elf = assemble(prefix, payload, files, info)
            binary = package(payload, elf, output, info)
        full_source = output / f"{PACKAGE}-{info['version']}-complete-source.tar.gz"
        complete_source(full_source, files, info)
        result = {"version": info["version"], "source_commit": info["source_commit"],
                  "distribution": "Ubuntu 24.04", "architecture": "amd64",
                  "package": binary.name, "package_sha256": digest(binary.read_bytes()),
                  "complete_source": full_source.name, "complete_source_sha256": digest(full_source.read_bytes())}
        (output / "ubuntu-build.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(f"Prepared Ubuntu package and complete source: {output}")
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Ubuntu package build failed: {error}\n")


if __name__ == "__main__":
    main()
