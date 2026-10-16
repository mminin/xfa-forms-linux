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
| Claude Opus 5.5, as credited in existing commit trailers | Initial XFA engine, detection and rendering APIs, scripting, layout, initial Evince integration and fixes through Poppler 0007 and Evince 0006; later source-package cleanup and the federal-form corpus. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Poppler 0008: preserve radio-button appearance states in ordinary PDF exports, with save/reopen regression coverage. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Poppler 0009: save and restore the live XFA form, scripts and form state; CLI support and regression coverage for saving, reopening and generating output again. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Evince 0007: complete editor restoration after re-rendering, including deferred combo-close callbacks, allocation and stale focus handling. |
| OpenAI Codex, GPT-6.1 Sol, reasoning effort `high` | Evince 0008: make Select All select text in the active form editor. |

Codex also added the focus regression driver (`tools/headless/check-focus.py`),
fixed headless test paths and metadata placement, implemented the desktop launcher
installer (`scripts/install-desktop.py`), performed GUI and save/reopen checks,
and drafted the original publication plan. Shared build scripts, the initial GUI
harness and the initial consent-letter scenario predate that handoff; later
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
> regression checks and desktop integration. The human maintainer is responsible
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
