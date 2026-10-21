# PR plan and contribution attribution

This is the publication handoff for the clean source package. No upstream
submission has been made. Keep the attribution below when splitting patches,
squashing commits or preparing merge request descriptions.

## Verified OpenAI model metadata

The Codex session used to complete the initial Claude handoff records:

- Assistant: OpenAI Codex.
- Model: **GPT-6.1 Sol**, model identifier `gpt-6.1-sol`.
- Reasoning effort: **high**.
- Evidence: the session's local `turn_context` records, checked on 2026-10-16.

The recorded model and effort are consistent across the session records from
October 13–16, 2026. “High” is the reasoning setting. For publication, use
“GPT-6.1 Sol with high reasoning effort.” Private session transcripts are not
part of the public package.

## Contribution breakdown

Patch numbers refer to the current series in `patches/`.

| Contributor / assistant | Work |
|---|---|
| Human maintainer, mminin | Directed the work, provided requirements and interactive feedback, and owns review, publication and maintenance. |
| OpenAI Codex (2026-10-20 packaging follow-up) | Matching print-preview helpers; release archive and checksum tooling; isolated Ubuntu package and complete-source builds; Evince 0022 for a separate desktop identity, 0023 for dropdown mouse activation and 0024 for consistent daemon identities; standard D-Bus activation-file installation; clean-container installation, runtime, printing and removal checks, with fresh-bus and held-click regressions. |
| OpenAI Codex (2026-10-19 editing audit) | Evince 0018–0021 and Poppler 0040–0047: multiline and editable-choice editing, document-action commits, input filters, Unicode appearances, rendering synchronization, field addressing, script locals, deep-tree handling and instance-manager resolution. Added the corpus edit/save/reopen sweep and expanded GUI/core regressions; see [TESTING.md](TESTING.md). |
| Claude (Opus 5.5 and 4.8, as credited in existing commit trailers) | Initial XFA engine, detection and rendering APIs, scripting, layout, initial Evince integration and fixes through Poppler 0007 and Evince 0006; later source-package cleanup, the federal-form corpus, Poppler 0010–0021 (images, tables, scripting, data DOM, FormCalc, validation, barcodes, formatting, pagination, focus and dialog API), Poppler 0026 (truncated images), Poppler 0027 (bounding recursive tree walks) and Evince 0012-0013 (teardown fix and Reader-style URL confirmation), the last three under Opus 4.8, and Evince 0009 (script-requested focus); under Opus 5.5, Poppler 0028–0039 (image size arithmetic, API warnings for script URLs, locales in picture clauses, the rest of FormCalc, SOM predicates, Acrobat's Doc object as `event.target`, bounded preorder walks, data binding, embedded copies of linked images, system fonts for characters the standard fonts lack, rotation, space above text) and Evince 0014–0017 (editor allocation, saved values in reopened editors, persistent script-URL sites and policy, Ctrl+wheel zoom). |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Poppler 0008: preserve radio-button appearance states in ordinary PDF exports, with save/reopen regression coverage. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Poppler 0009: save and restore the live XFA form, scripts and form state; CLI support and regression coverage for saving, reopening and generating output again. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Evince 0007: complete editor restoration after re-rendering, including deferred combo-close callbacks, allocation and stale focus handling. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Evince 0008: make Select All select text in the active form editor. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Poppler 0022–0025 and Evince 0010–0011: complete the interactive question/prompt UI, exclude waiting time from script deadlines, preserve callback lifetimes and test callback replacement, cancellation and re-rendering; reject corrupt state, deep nesting and output errors; commit editors outside focus transitions. |

Codex also added the focus regression driver (`tools/headless/check-focus.py`),
fixed headless test paths and metadata placement, implemented the desktop launcher
installer (`scripts/install-desktop.py`), performed GUI and save/reopen checks,
and drafted the original publication plan. The follow-up added the synthetic
Evince dialog test (`tools/headless/check-dialogs.c`, `scripts/test-dialogs.sh`)
and refreshed the 129-form corpus results and remaining-gap notes. Shared build
scripts, the initial GUI harness and the initial consent-letter scenario predate that handoff; later
packaging edits may include further Claude changes.

Mozilla's pdf.js XFA implementation was consulted as a reference for the initial
engine, as recorded in the README. Preserve upstream notices and existing human
and assistant credits. Git author names alone do not identify which assistant
was used.

## Suggested publication wording

> Developed under the direction of mminin with assistance from Anthropic
> Claude Opus 5.5 and OpenAI Codex using GPT-6.1 Sol (`gpt-6.1-sol`) with high
> reasoning effort. Claude assisted with the initial XFA engine and viewer
> integration and subsequent packaging. Codex assisted with editor restoration,
> Select All, radio-button export behavior, live XFA save/reopen support,
> script question/prompt dialogs, regression checks and desktop integration. The human maintainer is responsible
> for reviewing and maintaining the submitted changes.

For an individual merge request, narrow this wording to its actual patches.

## Submission sequence

1. Recheck each target project's current contribution and AI-assistance policies,
   existing reports and current branch before submitting. Reproduce ordinary
   viewer bugs separately and assess any adaptation needed for GNOME Papers.
2. Submit independent viewer fixes (Evince 0002–0005 and 0008) separately, with
   minimal ordinary-PDF examples. Extract the final combo-box fix, including
   relevant follow-up changes in 0006–0007.
3. Propose the small Poppler form-detection API changes (0001–0002) with tests.
4. Discuss the XFA engine design, optional scripting dependency and integration
   with maintainers before proposing the larger implementation. Separate editor
   lifecycle changes and dependent API work into reviewable submissions.
5. Review Poppler 0008 and 0009 separately. Document that the saved-state format
   in 0009 is specific to this patched implementation; ordinary PDF export and
   live saving have different interoperability properties.
6. Before publication, run the package's build and tests afresh, record failures
   and compatibility limits, and use synthetic data in public reproductions.
   Carry the relevant attribution into each submission and the release notes.

## Follow-up verification (2026-10-16)

The newer editing and sanitizer audit is recorded in [TESTING.md](TESTING.md).
The results below describe the earlier 2026-10-16 build.

- Rebuilt and installed the patched Poppler and Evince in the local development
  prefix. The system packages are unchanged.
- Passed all four form-detection tests and all 14 synthetic XFA tests, including
  save/reopen, scripting, dialog cancellation, a six-second answer delay and
  replacing callbacks while one is running.
- Passed the synthetic Evince dialog integration test on a private Wayland
  display: all question button sets, prompt defaults and editing, cancellation,
  four successive re-renders and closing the parent window while a script waits.
- Generated the consent letter with synthetic answers in screen and print modes;
  both outputs contained the expected child's name.
- Rendered all 129 corpus forms without a failed render. 119 logged no script
  errors; 10 logged 26 error occurrences. See [corpus/README.md](corpus/README.md)
  for the remaining script and image failures and the limits of this check.
- Applied all 23 Poppler patches and 10 Evince patches to fresh checkouts of the
  pinned bases and compared their resulting trees with the tested sources.
- Passed all 14 XFA tests under AddressSanitizer and UndefinedBehaviorSanitizer,
  including leak checking after explicit test-process graphics cleanup
  (`cairo_debug_reset_static_data()` and `FcFini()`). Without that cleanup,
  Fontconfig retained 320 bytes at process exit. The sanitizer build used
  `-fsanitize=address,undefined -fno-sanitize=vptr -fno-omit-frame-pointer
  -fno-sanitize-recover=undefined`; vptr checks were disabled for Poppler's
  hidden/no-RTTI types. These checks covered Poppler; the GUI integration test
  used the normal Evince build.

The feature work is available for review. Full compatibility with the remaining
forms, startup-script dialogs and the broader gaps in the README remain future
work; this verification does not establish submission-ready output for every form.

## Commit attribution audit — 2026-10-21

The October 19–20 editing and packaging session records also identify
GPT-6.1 Sol (`gpt-6.1-sol`) with high reasoning effort. Those records were checked
on October 21; automatic approval-review sessions were excluded.

The first prerelease history contains 16 primary Codex commits without AI
trailers and two mixed import commits missing Codex credit. The table below
records the original and repaired hashes, so attribution remains available in
clones of either history. This omission already existed in original Codex
commits; it was not solely introduced by the maintainer-identity rewrite.

| Original commit | Repaired commit | Work | Codex contribution |
|---|---|---|---|
| `0b0a569` | `5a468a3` | XFA forms in Evince: patches for Poppler and Evince | Imports Codex's Poppler 0008–0009 and Evince 0007–0008; retains Claude's original engine and integration credits. |
| `6bbfca5` | `58689e3` | Document verified Codex model and contribution attribution for publication | Primary implementation, verification or documentation |
| `b2a0705` | `9df7041` | Complete script question and prompt dialogs in Evince | Primary implementation, verification or documentation |
| `b3d6c1d` | `de0d8a1` | Record verification and remaining compatibility limits | Primary implementation, verification or documentation |
| `52afdba` | `5380c1b` | Detect interrupted bootstraps and verify downloads before replacing the cache | Primary implementation, verification or documentation |
| `107aebc` | `fa4df25` | Refuse truncated TIFF and GIF images; harden corrupt-state handling | Imports Codex's Poppler 0024–0025 and Evince 0011 alongside Claude's Poppler 0026. |
| `15c801e` | `ccb7666` | Keep multiline form edits and cover focus-out and Tab regressions | Primary implementation, verification or documentation |
| `2ae0d78` | `979a0be` | Audit form editing and restoration; fix commit, scripting and rendering failures | Primary implementation, verification or documentation |
| `3f4a80e` | `3a8ab29` | Keep desktop print previews on the local viewer and backend | Primary implementation, verification or documentation |
| `003fdce` | `bf7c810` | Prepare 0.1.0 experimental source release | Primary implementation, verification or documentation |
| `a885161` | `80ebedb` | Record fresh 0.1.0 source-package verification | Primary implementation, verification or documentation |
| `78a9ecd` | `6edecae` | Add Ubuntu 24.04 package and complete source builds | Primary implementation, verification or documentation |
| `1dcd09b` | `4319f79` | Isolate Ubuntu desktop identity and add package regression coverage | Primary implementation, verification or documentation |
| `dd26650` | `eb0bc8d` | Install profile icons under the packaged application ID | Primary implementation, verification or documentation |
| `65203ea` | `d658d13` | Record Ubuntu package verification and normalize installed permissions | Primary implementation, verification or documentation |
| `353ca70` | `969bfc3` | Fix daemon activation and mouse dropdowns in Ubuntu revision 2 | Primary implementation, verification or documentation |
| `692e744` | `7358b90` | Align daemon activation names with the packaged application ID | Primary implementation, verification or documentation |
| `9665670` | `c05c975` | Record verified Ubuntu revision 2 desktop and upgrade behavior | Primary implementation, verification or documentation |

The 25 Codex-written patches are Poppler 0008–0009, 0022–0025 and 0040–0047,
and Evince 0007–0008, 0010–0011 and 0018–0024. Their standard Codex co-author
trailers are restored throughout the exported history and in the upstream
commits used for future patch exports. Evince 0023–0024 previously contained
only `Assisted-by` credits.
The original engine and the other documented Claude contributions retain their
existing Claude credits. Follow the [commit attribution policy](CONTRIBUTING.md#ai-attribution)
for new commits and patch exports.
