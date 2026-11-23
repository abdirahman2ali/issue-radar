# 0001. Publish the existing `triage.json` as the JSON export

Status: accepted (SPIN-6). Risk tier: serious.

## Context

SPIN-6 asked for a JSON export so other tools can read results. The pipeline already writes the
full result set to `data/triage.json`, `scripts/publish_data.sh` force-pushes it to the `data`
branch, and `deploy.yml` serves it at `https://issue-radar.dev/triage.json`. The only written
description of its shape was `site/src/types.ts`.

## Decision

Build no export code. Document the existing file in the README ("Use the data") and keep that
documentation true with `tests/test_triage_json_doc.py`, which checks the documented fields against
a synthetic sample (`tests/fixtures/triage_sample.json`), runs the README examples against it, and
checks the security wording. The test makes no network calls.

Design A (Staff Software Engineer) was chosen. No second design exists: the Design Challenger's
runtime failed, so the owner was asked to waive or fix that step.

## Rejected

- A CLI export flag, a CSV format, a new endpoint or a new output directory: a second source of
  truth for data that is already published.
- `schema_version` and a CLI `--print`: both change a public interface. Each is a separate issue.
- A one-off live check script in the repo: it would drift. The live check is run once and quoted in
  the PR instead.

## Consequences

- The file is now a documented contract. Fields may be added; renaming or retyping one is a
  breaking change and needs the owner's approval.
- `title`, `excerpt`, `labels` and `author` are attacker-controlled public text. `redact()` only
  matches a few token formats. The documentation must say so and must not describe the text with
  the words "sanitized", "safe" or "clean". The test enforces this for the README section.
- Only the current file is served. The `data` branch is force-pushed, so its history is not an
  archive.
- If the README section grows well past 60 lines, move the field tables to `docs/triage-json.md`
  and link it.
