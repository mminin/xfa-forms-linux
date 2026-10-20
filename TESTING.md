# Editing and printing audits

## 0.1.0 source-release verification — 2026-10-20

The archive generated from public candidate `526964b` was extracted into a fresh
directory and built from scratch on Ubuntu 24.04, x86-64, using GCC 13.3.0,
CMake 3.28.3 and Meson 1.3.2, with four parallel build jobs. The build used local
Git mirrors of the pinned upstream sources. A separate fresh extraction fetched
all four upstream repositories over HTTPS and applied all 47 Poppler and 21
Evince patches successfully. Both bootstraps reproduced the development source
trees exactly. The official sample download also matched its pinned checksum.

The extracted build passed:

- Four form-type and 24 XFA GLib tests, plus the consent-letter scenario.
- 28 core regressions, including the enabled `/dev/full` output-failure check.
- 71 FormCalc expressions, nine package tests and 11 release-archive tests.
- 15 GUI integration tests and 14 printing scenarios on an isolated desktop.
- Screen and print consent-letter generation with the expected synthetic answer.
- Desktop launcher validation in a temporary applications directory.

These are normal-build release checks. The earlier sanitizer and corpus audits
below cover the same engine patch trees; they were not repeated for packaging.
The final source package adds this verification documentation to the tested
candidate without changing its patches, build scripts or tests. Checksums and
the public source commit are recorded in the generated release assets.

## Printing follow-up — 2026-10-20

The original audit checked print-mode PDF generation and active-editor commits,
but missed the external desktop preview launch. The launcher inherited the system
`PATH`, so GTK's `evince --preview` command selected the system viewer and
previewer. The system previewer's AppArmor profile then denied executable mapping
of the local PDF backend, producing “failed to map segment from shared object”.

The launcher now puts its own installation's `bin` directory first, keeping the
viewer, previewer and PDF backend together. AppArmor and system configuration are
unchanged. The failure was reproduced in the real UI before the fix, then the
same two-page PDF rendered successfully in preview afterwards.

`scripts/test-printing.sh`, run on the isolated desktop, covers 14 scenarios:
preview, Print to File and cancellation for ordinary PDFs and XFA forms through
both direct and export printing, plus two launcher checks starting with a system
`PATH`. The checks verify the actual preview process's executable and loaded PDF
backend, and compare page counts and text in the preview and output PDFs. Fixture
and settings paths include spaces and apostrophes. All jobs select Print to File;
these checks do not test a physical printer or its driver.

An additional UI check used the Print button inside preview and verified the
resulting two-page PDF. The ordinary 17-page PDF from the reported failure also
printed to a file successfully, preserving the page count and article text.

Artifacts are written under `_work/qa/printing-regressions/`. Start a new viewer
process through `scripts/run-evince.sh` after updating the launcher.

## Editing and sanitizer audit — 2026-10-19

The audit started with IMM 1295 text disappearing after leaving an editor. It
expanded beyond blank-form rendering to real editor commits, document actions,
script input filters, Unicode, concurrent rendering, and saved-form restoration.
All document edits used synthetic fixtures or unfilled public corpus forms.

## Bugs found and fixed

| Area | Failure | Regression coverage |
|---|---|---|
| Active editor | Closing a fresh form could discard the first answer without a save prompt | Active and detached pending editors are committed before checking modifications, saving or printing; save/reopen and a script replacing the document during commit |
| Editable choices | Free text did not commit on focus-out or Enter; capitalization-only changes were ignored | Both commit paths and a second edit changing only case |
| Multiline limits | Paste and insertion ignored the field's character limit | A Unicode paste truncated at a character boundary and then committed |
| Input scripts | Changes to `event.change`, cancellation and `rc` were discarded | Uppercase conversion, rejecting an appended character, deletion, Unicode, text cancellation and choice cancellation |
| Unicode appearances | A value could retain letters that disappeared from its rendered widget | Latin Extended, Cyrillic, Greek and Chinese, four rotations, save/reopen cycles and a real editor commit |
| Rendering concurrency | A commit freed a string while a render worker was generating a multiline appearance | Reproduced in repeated sanitized GUI runs; document synchronization, a concurrent GLib test, then 15 successful GUI stress repetitions |
| Exported field addressing | IMM 5669 imports failed beneath an unnamed subform | Direct exported-node addressing and generated SOM expressions resolving back to their original nodes |
| Script scope | Local variables could overwrite equally named form fields | A local variable leaves the field intact; deep-tree creation now builds the intended tree |
| Instance-manager paths | `resolveNode("Group._Row")` returned null; the old scope bug had masked this in three IRCC forms | Qualified, relative and global lookup, adding an instance, and retesting the affected forms |
| Tree lifetime and layout | Deep trees overflowed during destruction or measurement; cyclic appends leaked ownership | Iterative destruction, a smaller layout recursion budget, rejected ancestor/self appends, 6,000-node fixtures on a 1 MB stack |

The exact IMM 1295 page 3 given-name field was checked interactively through
editing, leaving, reopening the editor, saving and reopening the PDF. Closing
while that field was still active was reproduced without a save prompt before
the fix and with a save prompt afterwards.

## Coverage and results

- **Initial 129-form blank baseline:** rendered, saved with reusable XFA state, and reopened under
  AddressSanitizer, UndefinedBehaviorSanitizer and LeakSanitizer. Page counts,
  extracted text and normalized widget values survived the round trip.
- **129 edited forms, 430 edits:** up to three editable text fields and one choice were
  changed per form, then saved and reopened. The comparison includes all widget
  values, field properties, selected radio children, page counts and extracted
  text. Generated node serials are normalized, because restoration assigns new
  serials. The one form-authored recalculation is described below.
  The instance-manager fix was followed by another sanitized edit/save/reopen
  check of IMM 5406, IMM 5562 and IMM 5707 and a fresh blank-render check of all
  129 forms. The latter again rendered every form, with 125 logging no script
  errors and the four previously documented form-script failures unchanged.
- **15 GUI integration tests:** normal and sanitized Evince builds, including
  modal-dialog cancellation, model replacement, Tab transitions, active-editor
  saves, multiline limits, editable choices and Unicode appearances.
- **28 Poppler GLib checks:** four form-type cases and 24 XFA tests, including
  concurrent rendering and editing; run with the sanitizers.
- **28 synthetic core regressions:** malformed and deep XML, saved state,
  scripting deadlines, tiny stacks, field filters, generated field addressing,
  rotated Unicode appearances, ten save/reopen cycles, and output failures.
  The `/dev/full` check was enabled for the sanitizer run.
- **71 FormCalc expressions**, six offline package/bootstrap regressions, and
  image reference checks plus **43,000 deterministic decoder mutations**.
- The consent-letter scenario generated the expected letter in screen and print
  modes using made-up data.
- All 47 Poppler and 21 Evince patches apply cleanly to their pinned upstream
  bases.

CLI and GLib leak checks suppress Fontconfig/Expat process-global allocations.
GUI runs check memory access and undefined behavior; GUI leak detection is
disabled because of framework lifetime allocations. The image mutation run used
the standalone decoder probe. These checks do not establish full XFA compliance
or verify the legal or numerical correctness of every real form's answers.

### Expected INNS3 year recalculation

`inns3-fill-19e.pdf` has a layout-ready script that unconditionally assigns the
current year to `Page1.Instalment`; its second globally bound field follows it.
An edit clearing that year is therefore replaced on the next layout after
reopening. This is the template's explicit instruction. The corpus test permits
only those two fields to become the current year, verifies every other field,
and checks that the text differs only by that year. It does not ignore arbitrary
round-trip mismatches.

## Repeating the checks

After building, downloading the corpus, and selecting a Python environment with
`pikepdf`:

```sh
scripts/test.sh
python3 tools/qa/test_core.py
python3 tools/qa/test_formcalc.py
python3 tools/qa/test_package.py
XFA_QA_CORPUS=corpus/files XFA_QA_OUTPUT=_work/corpus-edit \
    python3 tools/qa/test_corpus.py
```

The corpus sweep writes per-form PDFs, logs and `results.json`. Unicode rendering
checks require fonts covering the tested scripts, such as DejaVu and Noto CJK.
The image tests additionally require Pillow and an `IMAGE_PROBE` executable built
from `tools/qa/image-probe.cc`.

On Ubuntu, optional QA packages include `python3-pikepdf`, `python3-pil`,
`python3-xlib` and `fonts-noto-cjk`. Use `/usr/bin/python3` for these distribution
Python packages, or install the corresponding modules in the selected virtual
environment. The core, package and release-archive tests use Python's standard
library and the build's command-line tools.

Run `scripts/test-dialogs.sh` on an isolated display, as described in the main
README. `PDFXFA` selects an alternate CLI binary for the Python tests. A build
with `-fsanitize=address,undefined` can be used with leak checking enabled and the
process-global suppressions noted above. Keep the selected build unchanged while
tests use its shared libraries.

Change scripts still run on field commit rather than on every keystroke. Font
metrics, unsupported container rotation and the other existing limits remain
listed in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

Use a short private `XDG_RUNTIME_DIR` for the headless desktop, for example one
created with `mktemp -d /tmp/xfa-runtime.XXXXXX`. Unix socket paths are limited
in length; a runtime directory deep inside an extracted build can exceed that
limit before GNOME Shell starts.
