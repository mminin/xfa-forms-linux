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

### 1. 32-bit overflow in image dimension arithmetic — P2
`poppler/XFAWriter.cc:474` computes the display size as `img->width * 72 / dpiX`
in `int` arithmetic. The image decoder accepts widths up to `maxPixels` (2^26) in
`poppler/XFAImage.cc`, so `width * 72` overflows a 32-bit `int` for widths above
~29.8 million.

**Why it matters:** signed overflow is undefined behaviour (UBSan flags it) and
yields a wrong `/Width`/`/Height` in the emitted PDF. It is *not* memory corruption —
the value is only used as a numeric dimension — so the impact is a malformed object,
not a crash or a write. It escaped the prior UBSan run only because no corpus image
is that wide.

**Fix:** do the multiplication in `long long`, or lower `maxPixels` to a value whose
`* 72` cannot overflow. One line either way.

### 2. URL "remember" is session-scoped, not persistent — P2
Evince 0013 mirrors Adobe Reader's Trust Manager prompt (Allow/Block, "remember this
site"), but the remembered per-host decisions live in an in-memory `GHashTable` on the
`EvView` (`priv->form_url_sites`). They are lost when the window closes, and there is
no global policy (Reader offers allow-all / block-all / ask, plus an admin-managed
list).

**Why it matters:** Acrobat/Reader parity is "follow the canon" per the user's
instruction, and the canon persists the list across sessions and exposes a policy
setting. The current gate is safe (it defaults to prompting) but forgets choices.

**Fix:** persist the allow/block list (GSettings) and add a Trust-Manager-style
preference. Decide whether "remember" should be app-wide (Reader) or per-window
(current). Deferred intentionally for the first debut; prompt-every-session is the
safe default.

### 3. The URL gate is Evince-only, by design — P3 (document, not fix)
`pdfxfa` (the CLI) only *prints* `launchURL`/`print` host requests; it never opens
anything, so it needs no gate. Any *other* glib host that wires up
`poppler_document_xfa_take_urls()` must implement its own confirmation — poppler
hands over the URLs without judging them. Worth a sentence in the glib API docs so a
future host does not repeat the silent-open mistake.

---

## Test and harness

### 4. `/view/xfa-dialogs` crashes in the headless harness — P1 (for the test), pre-existing
`tools/headless/check-dialogs.c`'s `xfa-dialogs` test aborts under the headless
session: first a `gtk_widget_size_allocate()` with width -18, then (after a geometry
tweak) "Trying to snapshot GtkEntry without a current allocation".

**Confirmed pre-existing:** stashing all of this session's `ev-view.c` changes and
rerunning against stock-patched Evince reproduces the same crash, so it is not caused
by the URL-gate or teardown work. It is the prior session's unfinished harness WIP.

**Why it matters:** the full `scripts/test-dialogs.sh` suite cannot run green until
this is resolved; `/view/launch-url` and `/view/editor-document-change` pass in
isolation. The crash is in the *test's* drive pattern (creating/triggering a form-field
editor via the backend while a modal nested loop runs), so it is likely a test-side
allocate/snapshot ordering problem, not a user-facing bug — but confirm that before
dismissing it.

**Fix:** investigate the form-field editor widget's allocate→snapshot cycle when the
field is driven without a realized, sized view; either stabilise the test or fix the
view if a real snapshot-before-allocation path exists outside the test.

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

### 6. FormCalc is partial — P2
Translated to JavaScript, but without SOM predicates (`a.[b > 1]`), the financial
functions, or picture-clause functions such as `Format()`/`Parse()`. **Why:** these
were not needed by the corpus forms. A form using them will throw at runtime.

### 7. Data binding is simplified — P2
Values are matched to data by name. `dataRef`/`bind` expressions are ignored, and the
form's values are held in the form tree, not written through to the data DOM the way
a strict implementation would. **Why:** name-matching covered the corpus; `dataRef`
forms will bind the wrong nodes or not at all.

### 8. Picture clauses are partial — P3
Numbers, dates and text only — not times — and symbol tables are English or French.
**Why:** the tested forms are en/fr CA. Other locales format wrong.

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

See the commit messages of those patches for detail.
