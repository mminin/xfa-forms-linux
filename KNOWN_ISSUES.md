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

### 7. Data binding is simplified — P2
Values are matched to data by name. `dataRef`/`bind` expressions are ignored, and the
form's values are held in the form tree, not written through to the data DOM the way
a strict implementation would. **Why:** name-matching covered the corpus; `dataRef`
forms will bind the wrong nodes or not at all.

### 9. Fonts are the 14 standard PDF fonts — P3
No embedding; narrow/black faces are approximated with horizontal scaling. **Why:**
embedding is a large addition. Glyph coverage and metrics will differ from Acrobat for
non-Latin text.

### 10. Images: no SVG, no external/linked images — P3
JPEG/PNG/GIF/BMP/TIFF data is drawn; SVG and `href`-linked images are not. 5 corpus
forms still show unsupported images (see `corpus/README.md`). **Why:** SVG needs a
rasteriser; linked images need fetching, which is a security decision of its own.

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

See the commit messages of those patches for detail.
