# Preparing a release

Release from the clean public repository. Its `VERSION`, release notes, patch
series and test results must describe the same candidate. The private development
repository and its history are not release inputs.

## Candidate checks

1. Review [RELEASE_NOTES.md](RELEASE_NOTES.md), [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
   and [TESTING.md](TESTING.md). Preserve patch authorship and attribution.
2. Use a fresh checkout, install the documented dependencies, then run
   `scripts/bootstrap.sh`, `scripts/build.sh` and `scripts/test.sh`.
3. Run `python3 tools/qa/test_core.py`, `python3 tools/qa/test_formcalc.py`,
   `python3 tools/qa/test_package.py` and `python3 tools/qa/test_release.py`.
   `XFA_QA_DEV_FULL=1` enables the core output-failure check on Linux.
4. On the private desktop, run `scripts/test-dialogs.sh` and
   `scripts/test-printing.sh`. Printing tests select Print to File.
5. Download the sample and run `tools/consent-letter-scenario.sh` in screen and
   print modes. Recheck the corpus when engine behavior changes, using the
   procedures and optional dependencies in `TESTING.md`.
6. Commit the candidate, then run:

   ```sh
   python3 scripts/prepare-release.py --check
   python3 scripts/prepare-release.py
   cd _work/releases/0.1.0
   sha256sum -c SHA256SUMS
   ```

The packager accepts a clean, committed public tree only. It rejects submodules,
symlinks, unexpected paths and binary files. It creates a deterministic source
tarball, a public-commit manifest, release notes and their checksums. It does not
fetch dependencies, run tests, tag, push or publish. Building the tarball still
requires fetching the upstream repositories listed in `UPSTREAM`.

Extract the tarball and repeat bootstrap/build and the relevant tests from that
extraction before uploading it. Record the candidate's public commit and logs.
Use an empty output directory for a changed candidate; existing differing release
assets are never replaced.

## Ubuntu package

On Ubuntu 24.04 amd64, install the normal build dependencies plus `bubblewrap`,
`dpkg-dev` and `binutils`. After a clean public bootstrap, run:

```sh
python3 scripts/build-ubuntu-package.py
python3 scripts/prepare-release.py --ubuntu-assets _work/ubuntu-package/assets \
    --output _work/releases/0.1.0-ubuntu
```

The builder compiles at a fixed `/opt/xfa-forms-linux` prefix inside a private
mount namespace. It writes only to its work directory, strips runtime binaries,
calculates dependencies with
[`dpkg-shlibdeps`](https://manpages.debian.org/bookworm/dpkg-dev/dpkg-shlibdeps.1.en.html),
and packages the private libraries with the viewer and desktop launcher. It also
exports the exact complete source with a per-file manifest, including QuickJS and
Zint. A complete source extraction can run the same builder without a Git checkout.

Test installation, ordinary PDFs, XFA forms, printing and removal in a clean
Ubuntu 24.04 container before publishing. Verify all release checksums and ship
the complete source alongside the binary. The combined release manifest rejects
binaries built from another public commit or altered assets.

## Publication

Once the candidate and destination are approved, create an annotated `v0.1.0` tag
on the public commit recorded in `release.json`. Publish from the public
repository, mark the release as experimental/prerelease, use `RELEASE_NOTES.md`
as its description, and attach both source archives, the Ubuntu `.deb`,
`release.json` and `SHA256SUMS`.

No remote hosting destination is configured in the prepared local repository.
Choosing that destination and publishing are separate from preparing these assets.
