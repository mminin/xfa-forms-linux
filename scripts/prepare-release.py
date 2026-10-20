#!/usr/bin/env python3
"""Create checksummed release assets from a clean, committed public repository."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "xfa-forms-linux"
DOCUMENTS = {
    ".gitignore", "COPYING", "README.md", "VERSION", "UPSTREAM",
    "KNOWN_ISSUES.md", "TESTING.md", "PR_PLAN.md", "CONTRIBUTING.md",
    "RELEASE_NOTES.md", "RELEASING.md",
}
REQUIRED = {"COPYING", "README.md", "VERSION", "UPSTREAM", "KNOWN_ISSUES.md",
            "TESTING.md", "RELEASE_NOTES.md"}


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def allowed(path):
    p = PurePosixPath(path)
    if p.is_absolute() or any(x in (".", "..") for x in p.parts):
        return False
    if path in DOCUMENTS:
        return True
    if len(p.parts) == 2 and p.parts[0] == "scripts":
        return p.suffix in (".py", ".sh")
    if len(p.parts) == 3 and p.parts[0] == "patches":
        return p.parts[1] in ("poppler", "evince") and re.fullmatch(r"[0-9]{4}-.+\.patch", p.name) is not None
    if p.parts[0] == "corpus":
        return path in ("corpus/README.md", "corpus/forms.tsv", "corpus/results.tsv")
    if p.parts[0] == "tools":
        return (p.suffix in (".py", ".sh", ".c", ".cc", ".h")
                or path in ("tools/headless/.gitignore", "tools/headless/bin/ibus-daemon"))
    return False


def inspect():
    if Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve() != ROOT:
        raise ValueError("run from the public repository, not its private source templates")
    if git("status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("commit or preserve working-tree changes before preparing a release")
    version = git("show", "HEAD:VERSION").decode().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("VERSION must be a plain release version, for example 0.1.0")
    files = {}
    patches = {"poppler": [], "evince": []}
    for entry in git("ls-tree", "-rz", "--full-tree", "HEAD").split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.decode().split()
        path = raw_path.decode()
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError(f"release must contain regular files only: {path}")
        if not allowed(path):
            raise ValueError(f"unexpected release path: {path}")
        data = git("cat-file", "blob", object_id)
        if b"\0" in data:
            raise ValueError(f"binary release file: {path}")
        files[path] = data
        if path.startswith("patches/"):
            patches[PurePosixPath(path).parts[1]].append(int(PurePosixPath(path).name[:4]))
    missing = REQUIRED - files.keys()
    if missing:
        raise ValueError(f"missing release files: {', '.join(sorted(missing))}")
    if version not in files["RELEASE_NOTES.md"].decode():
        raise ValueError("release notes do not identify VERSION")
    for name, numbers in patches.items():
        if sorted(numbers) != list(range(1, len(numbers) + 1)) or not numbers:
            raise ValueError(f"{name} patches must be numbered consecutively from 0001")
    upstream = {}
    for line in files["UPSTREAM"].decode().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, url, base = line.split()
        if name in upstream or not url.startswith("https://") or not re.fullmatch(r"[0-9a-f]{40}", base):
            raise ValueError("invalid or duplicate pinned upstream entry")
        upstream[name] = {"url": url, "commit": base}
    if set(upstream) != {"quickjs", "zint", "poppler", "evince"}:
        raise ValueError("UPSTREAM must pin quickjs, zint, poppler and evince")
    return version, files, patches, upstream


def prepare(output=None, check=False):
    version, files, patches, upstream = inspect()
    commit = git("rev-parse", "HEAD").decode().strip()
    if check:
        print(f"Ready: {version}, public commit {commit}, {len(files)} files; "
              f"{len(patches['poppler'])} Poppler and {len(patches['evince'])} Evince patches")
        return
    output = (output or ROOT / "_work/releases" / version).resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "_work"):
        raise ValueError("use _work/ or a directory outside the source tree for release assets")
    name = f"{PROJECT}-{version}.tar.gz"
    archive = git("archive", "--format=tar", f"--prefix={PROJECT}-{version}/", "HEAD")
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as target:
        target.write(archive)
    payload = compressed.getvalue()
    manifest = {
        "project": PROJECT, "version": version, "status": "experimental",
        "source_commit": commit, "source_tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
        "archive": name, "sha256": hashlib.sha256(payload).hexdigest(),
        "patches": {key: len(value) for key, value in patches.items()},
        "upstream": upstream,
    }
    assets = {name: payload, "release.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
              "RELEASE_NOTES.md": files["RELEASE_NOTES.md"]}
    assets["SHA256SUMS"] = "".join(f"{hashlib.sha256(data).hexdigest()}  {path}\n"
                                  for path, data in sorted(assets.items())).encode()
    output.mkdir(parents=True, exist_ok=True)
    for path, data in assets.items():
        destination = output / path
        if destination.is_symlink() or (destination.exists() and destination.read_bytes() != data):
            raise ValueError(f"existing differing asset; use an empty output directory: {destination}")
    for path, data in assets.items():
        with tempfile.NamedTemporaryFile(dir=output, delete=False) as temporary:
            temporary.write(data)
            temporary_path = Path(temporary.name)
        temporary_path.chmod(0o644)
        temporary_path.replace(output / path)
    print(f"Prepared {version} from public commit {commit}: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="asset directory (default: _work/releases/VERSION)")
    parser.add_argument("--check", action="store_true", help="validate source without writing assets")
    args = parser.parse_args()
    try:
        prepare(args.output, args.check)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"release preparation failed: {error}\n")


if __name__ == "__main__":
    main()
