# XFA forms in Evince

Patches for [Poppler](https://poppler.freedesktop.org/) and
[Evince](https://gitlab.gnome.org/GNOME/evince) that let a free PDF viewer open
**dynamic XFA forms**: the kind of government form that every non-Adobe viewer
shows only as "Please wait… this document requires Adobe Reader 8 or higher".

With these patches the viewer lays out the form, runs its JavaScript, and lets you
fill it in. You can also generate the form's output document, print it, and save
and reopen the filled form, all locally on your own computer.

**Status: experimental.** It was developed against one real form, the Government
of Canada's [consent letter for children travelling outside Canada](https://travel.gc.ca/travelling/children/consent-letter)
(form 2123). It implements the XFA features that form uses, which is not general
XFA compatibility. Nothing here has been reviewed or accepted upstream yet.

[`corpus/`](corpus/README.md) measures 129 federal forms, including every fillable form
in the CRA's catalogue. 105 of them are dynamic XFA forms that Linux PDF viewers can't
open at all. Among them are most IRCC immigration applications and 90 tax forms, such as
the T1135 Foreign Income Verification Statement and the TFSA and FHSA returns. This
engine lays all of them out, but so far only the consent letter is verified to work
fully.

## What works

For the tested form, in the patched Evince:

- The real questionnaire appears instead of the "Adobe Reader" fallback page.
- Text fields, drop-downs, radio buttons and push buttons work.
- Sections appear and disappear as you answer, and rows can be added and removed.
- **Generate letter** builds the letter from your answers, and **Print letter**
  prints only those pages. Screen-only buttons are left off the printout.
- The English/Français switch keeps what you have entered.
- **Save a copy** keeps the form's scripts and its current state, so the saved file
  can be reopened, edited and regenerated. Reopening such a file needs this
  patched viewer; Adobe Reader and other viewers won't restore that state.
- **Print** or export gives an ordinary PDF that opens anywhere, without scripts.

Known gaps, most of them found with the [corpus](corpus/README.md):

- FormCalc runs translated to JavaScript, without SOM predicates (`a.[b > 1]`), the
  financial functions or picture-clause functions such as `Format()`.
- Data binding is simplified: values are matched to data by name, `dataRef` bindings
  are ignored, and the form's values are kept in the form, not in the data DOM.
- Picture clauses support numbers, dates and text, not times, and symbols are English
  or French.
- Fonts map onto the 14 standard PDF fonts, with horizontal scaling for narrow
  and black faces. Nothing is embedded.
- Images are drawn from JPEG, PNG, GIF, BMP and TIFF data; SVG and external
  (linked) images are not.
- Script message boxes are answered "Yes"/"OK" automatically and then shown, and
  `xfa.host.response()` prompts get their default answer.

## How it works

```
PDF with dynamic XFA ──► Poppler XFA engine ──► generated PDF pages with form fields ──► Evince
                          │ XFANode     XML parser, template, form and data DOMs
                          │ XFAForm     instance managers, SOM expressions, values, events, data
                          │ XFAScript   QuickJS + the XFA object model
                          │ XFAFormCalc FormCalc, translated to JavaScript
                          │ XFALayout   page areas, flowed, positioned and table layout, page breaks
                          │ XFAText     font metrics, rich text, line breaking
                          │ XFAImage    JPEG, PNG, GIF, BMP and TIFF images
                          │ XFAWriter   content streams, widgets, barcodes, PDF assembly
                          ▲
  field edits (poppler-glib setters) ┘ → form scripts run → Evince swaps in the re-rendered pages
```

- **Poppler**: the engine is in `poppler/XFA*`, with a command-line tool,
  `pdfxfa [-set som=value]... [-click som]... [-print] in.pdf out.pdf`.
  [QuickJS-ng](https://github.com/quickjs-ng/quickjs) runs the scripts and is an
  optional dependency (`ENABLE_XFA_SCRIPTING`); without it, forms are laid out in
  their initial state and no scripts run. [Zint](https://zint.org.uk/) encodes
  barcodes, also optionally (`ENABLE_XFA_BARCODES`). poppler-glib gains
  `poppler_document_get_form_type()`, `poppler_document_render_xfa()` and calls to
  collect messages, URLs and print requests that scripts make.
- **Evince**: the PDF backend renders XFA forms after loading. When an edit changes
  the form, the view swaps in the re-rendered document and keeps your place and the
  field you were editing. It also shows script messages, opens requested URLs and
  starts printing.

Form scripts run inside QuickJS with only the XFA and Acrobat objects implemented
here. They have no file or network access; a URL a form asks to open
(`app.launchURL`) opens in your browser.

## Build and try it (Ubuntu 24.04)

```sh
sudo sh scripts/install-build-deps.sh   # build dependencies, once
scripts/bootstrap.sh                    # fetch upstream sources and apply patches/
scripts/build.sh                        # build into ./_install; nothing is installed system-wide
scripts/fetch-sample.sh                 # download the tested form from travel.gc.ca
scripts/run-evince.sh samples/consent-letter-2123.pdf
```

`bootstrap.sh` checks out each project at the base commit listed in `UPSTREAM`
and applies the patches with `git am` on a branch named `xfa-support`. The patched
Evince uses the development profile (`org.gnome.Evince.Devel`), so it runs beside
your system's Document Viewer.

`python3 scripts/install-desktop.py` adds a "Document Viewer (XFA)" launcher for
your user, and `--make-default` also makes it your default PDF application.

Poppler's main branch needs CMake 3.28 or later and C++23 (GCC 13 works). Ubuntu
24.04's Gpgmepp is too old for it, so `build.sh` turns off GPGME, which only
affects signature verification. Evince's main branch uses GTK 4 and libadwaita,
unlike the GTK 3 Evince 46 that Ubuntu 24.04 ships.

## Tests

```sh
scripts/test.sh
```

This runs the synthetic Poppler tests, which build small XFA forms in memory:

- form detection: no form, AcroForm, dynamic XFA, static XFA
- rendering and script-driven re-rendering
- radio buttons across save and reopen cycles
- scripts and form state across save and reopen

If the sample form has been downloaded, it then also fills it in with made-up data
(`tools/consent-letter-scenario.sh`), clicks Generate letter, and checks that the
letter was produced.

`tools/headless/` drives the patched Evince on a private headless GNOME Shell
session with X11 input and screenshots, for testing the user interface without
touching your desktop. See the comments in `run-session.sh` and `drive.py`.

## Patches

Poppler (`patches/poppler/`, about 12,300 added lines):

| Patch | What it does |
|---|---|
| 0001–0002 | `poppler_document_get_form_type()` and `poppler_document_get_needs_rendering()` in poppler-glib, with tests |
| 0003–0004 | The XFA engine and the `pdfxfa` tool |
| 0005–0007 | Rendering XFA forms through poppler-glib, forwarding field edits, with a test |
| 0008 | Keep radio-button appearances intact in exported forms |
| 0009 | Save filled forms with their scripts and state, and reopen them |
| 0010 | Decode PNG, BMP and TIFF images, with transparency |
| 0011 | Lay out tables in columns |
| 0012 | Draw the values of read-only and image fields |
| 0013 | Scripting object model: form variables, script objects, item lists, colors and more |
| 0014 | The data DOM: `xfa.datasets`, drop-down lists bound to data, global fields, initial data |
| 0015 | FormCalc, translated to JavaScript |
| 0016 | Validation scripts of immigration forms: validation messages, `oneOfChild` |
| 0017 | Barcodes, drawn with Zint |
| 0018 | Picture clauses for display, editing and validation; validation results |
| 0019 | Pagination: page breaks after objects, keeping objects together, repeated table headers |
| 0020 | `xfa.host.setFocus()`: scripts move the viewer to a field |
| 0021 | Viewers answer the questions and prompts of scripts (glib API; Evince does not use it yet) |

Evince (`patches/evince/`, about 650 added lines):

| Patch | What it does |
|---|---|
| 0001 | Show dynamic XFA forms: render them, swap in re-rendered documents, messages, URLs, print ranges |
| 0002 | Combo boxes in forms never opened (GTK 4 port) |
| 0003 | The Save dialog was given a path as a URI ("The folder contents could not be displayed") |
| 0004 | The window lost track of whether a replaced document was modified |
| 0005 | Sidebar thumbnails stayed blank until something scrolled |
| 0006–0007 | Keep editing the field you went to when a form re-renders |
| 0008 | Ctrl+A selects the text of the field being edited, not the whole document |
| 0009 | Move to the field that form scripts ask for, such as the first one to correct |

Evince 0002–0005 and 0008 don't depend on XFA: they fix bugs that affect ordinary
PDFs in Evince's main branch as of the base commit.

To change a patch, commit in `upstream/<project>` on branch `xfa-support` and run
`scripts/export-patches.sh`.

## Upstream

None of this has been submitted yet. XFA is deprecated in PDF 2.0, and a script
engine is a large addition to a PDF library, so the plan is to discuss the design
with the Poppler and Evince maintainers before proposing the engine. The
independent Evince fixes and the form-detection API can be proposed separately.
GNOME's newer [Papers](https://apps.gnome.org/Papers/) document viewer is also
worth considering.

## Credits and AI assistance

Most of this code was written with AI coding assistants: Anthropic's Claude (commits
carrying a `Co-Authored-By: Claude` line) and OpenAI Codex using **GPT-6.1 Sol**
(`gpt-6.1-sol`, reasoning effort `high`; Poppler 0008–0009 and Evince 0007–0008).
The model and effort were verified against the local Codex session records.
The [PR plan](PR_PLAN.md) records the contribution breakdown and attribution to
carry into upstream submissions. The human maintainer, mminin <mminin2010@gmail.com>, directed
the work and is responsible for it. Mozilla's
[pdf.js](https://github.com/mozilla/pdf.js) XFA implementation was consulted as a
reference while writing the engine.

## License

GPL-2.0-or-later, the same as Poppler and Evince; see `COPYING`. The patches are
contributions to those projects under their licenses. QuickJS-ng (MIT) and Zint's
library (BSD-3-Clause) are downloaded by `bootstrap.sh`, not included here.

The tested form belongs to the Government of Canada and is not included in this
repository; `scripts/fetch-sample.sh` downloads it from the official site.
