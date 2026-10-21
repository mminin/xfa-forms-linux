# Contributing

For a bug report, include the release version, Linux distribution, whether the
viewer was started with `scripts/run-evince.sh`, the steps to reproduce, and the
expected and actual behavior. For printing, distinguish preview, Print to File
and a physical printer, and include the full error message.

Prefer a small synthetic PDF or a link to an unfilled public form. Include its
SHA-256, page and field when applicable. Screenshots and logs should use made-up
answers; avoid sharing filled personal, immigration or tax documents.

Build with the instructions in [README.md](README.md). Run `scripts/test.sh` and
the relevant checks described in [TESTING.md](TESTING.md). Core and package tests
can run without a desktop. The GUI and printing tests need a private display and
session bus. Keep build/install operations separate from tests using those same
libraries.

Change upstream code on its `xfa-support` branch, commit the change there, and
regenerate the patch series with `scripts/export-patches.sh`. Keep patches
focused, preserve author and license notices, and describe any AI assistance
used. Add a regression that reproduces a behavioral fix when practical.

For a suspected vulnerability, contact the maintainer at the address in
[README.md](README.md) before posting an exploit or a sensitive document publicly.
This is an experimental project without a formal security response SLA.

## AI attribution

Keep the human contributor as the Git author. For AI-assisted implementation,
documentation or verification, put the assistant's co-author trailer in both
its upstream commit and the aggregate source/export commit. For Codex, use:

```text
AI-Assistant: OpenAI Codex
AI-Model: gpt-6.1-sol
AI-Reasoning-Effort: high
Co-authored-by: Codex <noreply@openai.com>
```

Record the actual model and reasoning setting when verified; write `unknown`
when unavailable. The example above describes this project's verified Codex
sessions. Preserve existing Claude trailers and their recorded model names.
When importing work by both assistants, retain both credits and explain their
respective contributions. A review alone should be described as a review.

Keep the trailers when amending, squashing or exporting commits. Before
publication, inspect `git log --format=full` and the message headers in every
changed patch. Credits in README/PR_PLAN and `Assisted-by` prose do not replace
`Co-authored-by` commit trailers.
