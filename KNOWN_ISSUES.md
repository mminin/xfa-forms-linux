# Known issues and outstanding work

What still needs fixing in the XFA patch set, and why. This is the developer-facing
list; the user-facing "Known gaps" in [README.md](README.md) is a shorter summary.
Last reviewed 2026-10-19 (after the CPT121 report).

Items are grouped and tagged with a rough priority: **P1** (fix before a serious
upstream proposal), **P2** (should fix), **P3** (nice to have / documented limitation).

No known crash or security issue is open. What remains are documented limits of the
engine, each with the reason it stays, and one fidelity issue (#13).

---

## Fidelity

### 13. Text sits 1–3 points lower than in Acrobat — P2
Designer's render cache (`<?renderCache.textRun?>` in templates) records where
Acrobat puts each line of a draw. Over about 1,800 cached Helvetica draws in the
corpus, Acrobat puts the first baseline 0.775 × font size below the top of the
content, whatever the line height, and spaces lines by `lineHeight`, or 1.2 × size
without one. We put the first baseline at the font's ascent, 0.905 × size, and add
any extra line height above the line: 8 pt text is about 1 pt lower, 3 pt with an
11 pt line height. Without a line height our lines are also 0.08 × size closer.
**Why it is not fixed yet:** moving the first baseline only moves ink, but changing
line spacing changes the height of growable text, hence flowed layout and page
breaks across the corpus; it needs the same old/new corpus comparison as the
rotation fix, and per-font numbers for the other typefaces. Overlaps such as T1134
page 16, where a paragraph wraps one line more than in Acrobat and runs into the
next heading, come from the same metrics.

## Engine completeness (documented limitations)

These are design limitations, not regressions. Each is a real gap a strict XFA form
could hit; listed so nobody assumes full coverage.

### 7. `dataRef` bindings with predicates or expressions — P3
Bindings by reference follow simple paths (`$.a.b`, `$record.a[2]`, `$data.a`).
References with predicates or `[*]` bind nothing. **Why:** none of the 129 corpus
forms uses `dataRef` at all; the simple paths cover what Designer writes.

### 9. Fonts: the form's typefaces are not looked for — P3
Text uses the standard 14 fonts, and a similar system font only for characters they
lack. A form asking for Myriad Pro gets Helvetica even where Myriad Pro is installed.
**Why:** metrics of the standard fonts are known everywhere, so layout does not depend
on what the reader has installed. Chinese text embeds the subroutines of its CJK font
(about 1.5 MB); subsetting CFF subroutines would need a Type 2 charstring interpreter.

### 10. Images: SVG and linked images — P3
SVG images are not drawn (no corpus form has one). Linked images (`href` without an
embedded copy) are not loaded by design, as a document must not read local files or the
network; in the corpus they all point to files on the form author's computer, which
Acrobat cannot load either.

### 11. Non-interactive contexts auto-answer scripts — P3
Scripts that run before a view is attached, and all command-line rendering, answer
`app.alert`/`messageBox` automatically and use default `app.response` prompt text.
Only interactive editing in Evince shows real dialogs. **Why:** there is no user to
ask in those contexts. A form that branches on a docReady answer renders one branch.

### 12. IMM 5257 page 2 holds only the "office use" box — P3
Tracked separately; the template's own geometry explains it, and Acrobat appears to
lay it out the same way. Left as-is pending a counter-example.

### 14. Rotated subforms, areas and exclusion groups — P3
Draws and fields turn by their `rotate` attribute; containers do not, as turning
them means turning all their content. **Why:** no corpus form rotates a container;
the 357 rotated objects in the corpus are all draws and fields.

---

## Already fixed this cycle (for reference, no action needed)

- Image truncation bomb — tiny TIFF/GIF claiming huge sizes (poppler 0026).
- Script-built deep-tree stack overflow in the recursive walkers (poppler 0027).
- Silent `launchURL` → Reader-style Allow/Block gate (Evince 0013).
- Form-editor teardown crash on close-mid-edit (Evince 0012).
- Integer overflow in image size arithmetic (poppler 0028).
- glib API docs warn hosts that script URLs are unchecked (poppler 0029).
- Form editors allocated below their minimum size, or not at all while a form
  reloads, which crashed the `xfa-dialogs` headless test (Evince 0014).
- A form editor reopened by Tab showed the field's old value over the saved one
  (Evince 0015).
- Remembered URL choices now persist in settings, with an ask/allow/block policy
  for other sites that administrators can lock in dconf, as in Reader's Trust
  Manager (Evince 0016).
- Picture symbols and default patterns now come from the form's `<localeSet>`
  (en_CA forms showed `date.short{}` as US `M/D/YY`), time and date-time pictures
  are supported, and `null{}`/`zero{}` no longer swallow every value — 12 corpus
  currency fields showed raw numbers (poppler 0030).
- FormCalc gained its financial, time, `Format()`/`Parse()`, `WordNum()`, unit,
  `Eval()` and `Ref()` functions, checked against the examples of Adobe's FormCalc
  reference (`tools/qa/test_formcalc.py`) (poppler 0031), and SOM predicates
  (poppler 0032).
- `event.target` is Acrobat's Doc object: CRA forms tested `dynamicXFAForm`, took
  their AcroForm path and stopped before adding table rows; 483 script errors gone
  (poppler 0033).
- Preorder walks were not bounded in depth; setting a global field in a deep
  script-built tree crashed (poppler 0034).
- Data binding: values reach the data DOM, `dataNode` is real, `dataRef` simple paths,
  occurrences from data, `manifest.evaluate()`, plain-call `this`. The consent letter's
  language switch lost half the answers (conditional sections) each time; it now
  keeps them all. Four CRA paper-forms barcodes work (poppler 0035).
- Embedded copies of linked images are used (poppler 0036).
- Characters the standard fonts lack became `?`; 13 corpus forms had `?` for bullets
  and arrows, and any Cyrillic, Greek, Chinese or Polish name was lost (poppler 0037).
- `rotate` was ignored. 75 corpus forms turn rules or text a quarter; CPT121's date
  underlines became 42 mm bars down the page and RC4649's column headings spilled
  over its rows (poppler 0038).
- The space above the first paragraph of text was dropped when drawing, so captions
  sat on the rule above them; the render cache shows Acrobat keeps it (poppler 0039).
- Ctrl+wheel did not zoom: the view's GTK 4 scroll controller had no axes, an
  upstream bug of the port (Evince 0017).

- Verified before publishing (2026-10-19): a fresh clone of the public tree runs
  `scripts/bootstrap.sh` and `scripts/build.sh` from scratch, Zint included, and
  generates the same consent letter as the development build; `corpus/README.md` and
  `corpus/results.tsv` hold the current results (125 of 129 forms without script
  errors, the other 4 failing on mistakes in the forms themselves).

See the commit messages of those patches for detail.
