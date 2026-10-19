# Known issues and outstanding work

What still needs fixing in the XFA patch set, and why. This is the developer-facing
list; the user-facing "Known gaps" in [README.md](README.md) is a shorter summary.
Last reviewed 2026-10-19.

Items are grouped and tagged with a rough priority: **P1** (fix before a serious
upstream proposal), **P2** (should fix), **P3** (nice to have / documented limitation).

Nothing here is a known memory-corruption bug. The crashes listed are denial-of-service
(stack exhaustion or a GTK abort), not exploitable writes.

---

## Security and robustness

---

## Test and harness

### 5. Pending verification before publishing — P1
Carried over from the prior session and still not done:
- **Fresh public bootstrap + build test**, now that `upstream/zint` is a submodule —
  clone the public export clean and run `scripts/bootstrap.sh` + `scripts/build.sh`
  from scratch to confirm the zint path works for a new user.
- **Refresh the corpus grades**: `corpus/README.md` and `_work/corpus/results.tsv`.
  Current run: 0 failed renders, 5 forms with unsupported images, 26 forms still
  logging script errors.
- **Reconcile the script-error count**: the README narrative says errors fell to ~20;
  the latest `check-corpus.sh` reports 26 (the metric counts "script error"/"script
  object" log lines, a rough proxy). Decide on one number and make README, memory and
  `corpus/README.md` agree.

---

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

See the commit messages of those patches for detail.
