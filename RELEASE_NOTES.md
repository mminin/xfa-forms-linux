# XFA forms in Evince 0.1.0

First experimental release of the Poppler and Evince patches for opening,
editing, saving and printing dynamic XFA forms on Linux. The release contains
47 Poppler patches, 23 Evince patches, build scripts and regression tools.

## Features

- Render dynamic XFA forms and run their JavaScript and FormCalc locally.
- Edit text, choices and radio buttons; add rows and reveal conditional sections.
- Show script questions and prompts during interactive editing.
- Save a reusable filled form with its scripts and state, or print an ordinary PDF.
- Generate the Government of Canada consent letter from synthetic test answers.
- Keep form edits across focus changes, Tab, saves, printing and close checks.
- Render non-Latin answers with fallback fonts and load the matching local helper
  for print preview.

## Installation

An installable `xfa-forms-linux_0.1.0-2_amd64.deb` is provided for Ubuntu 24.04.
Install it with `sudo apt install ./xfa-forms-linux_0.1.0-2_amd64.deb`, then open
**Document Viewer (XFA)** or run `xfa-forms-linux document.pdf`. The viewer and
private libraries live under `/opt/xfa-forms-linux`; existing PDF-default settings
are left intact. Remove it with `sudo apt remove xfa-forms-linux`.

Package revision 2 fixes document-registration service discovery in existing
desktop sessions and GTK active-state warnings when opening form dropdowns with
the mouse. It upgrades revision 1 through the same install command.

The release also includes a complete source archive with all four upstream trees
and the applied patches. Its build instructions require no upstream source fetch.

The smaller patches-and-build-tools source package requires network
access to fetch four upstream projects at the revisions in `UPSTREAM`. The
documented and tested target is Ubuntu 24.04 on x86-64, with GCC 13, CMake 3.28 or
later, GTK 4 and libadwaita. See [README.md](README.md) for the commands.

The source build installs into `_install/` inside the source directory. Start it through
`scripts/run-evince.sh`; the launcher selects the matching libraries and preview
helper. Desktop integration and becoming the default PDF viewer are optional.
Keep the source directory in place after building: the installation uses its
absolute path.

## Compatibility and limits

This release is experimental and has not been accepted upstream. It does not
implement all of XFA or establish that every form's calculations and generated
output match Adobe Reader.

- All 129 forms in the public corpus render; 125 log no script errors. Four
  retain documented form-script failures. The editing audit covers 430 edits
  across the corpus; see [TESTING.md](TESTING.md) for scope and exceptions.
- Reusable saved forms restore their state in this patched viewer. Other viewers,
  including Adobe Reader, do not restore this implementation's saved state.
  Ordinary printed PDFs are interoperable.
- Font metrics can shift text and affect wrapping. Rotated containers and some
  data-reference expressions are unsupported. Change scripts run on field commit
  rather than on every keystroke.
- Signature verification is disabled in the supplied build configuration.
- Desktop printing was checked with preview and Print to File, including an
  ordinary 17-page PDF. Physical printers and their drivers were not tested.

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for the detailed limitations and
[CONTRIBUTING.md](CONTRIBUTING.md) for reproducible bug reports.

## Credits and license

Developed under mminin's direction with assistance from Anthropic Claude and
OpenAI Codex. Existing patch authorship and assistant credits are preserved; see
[PR_PLAN.md](PR_PLAN.md) for the contribution breakdown.

The package is GPL-2.0-or-later; see `COPYING`. Upstream projects retain their
licenses and notices. Government forms and filled documents are not distributed
in this source package.
