# issue-radar

A daily triage board for GitHub issues, classified by Jev (TypeSafe AI's System One model).

Once a day a GitHub Actions job pulls new issues from `anthropics/claude-code`, classifies each one with Jev (category, area, severity, urgency, regression, repro, needs info), publishes an interactive board to GitHub Pages, and incrementally loads the results into Databricks.

![CI](https://github.com/abdirahman2ali/issue-radar/actions/workflows/ci.yml/badge.svg)

Live board: https://issue-radar.dev/

## Status

Built: the pipeline, the daily workflow, the site, and CI/CD. Not built yet: the Databricks load and the live try-it box.

## Layout

```
issue-radar/
├── pipeline/   Python: fetch issues, classify with Jev, merge
├── site/       Vite + React + TypeScript board (filters, charts, detail drawer)
├── scripts/    publish_data.sh, force-pushes triage.json to the data branch
├── tests/      pytest for the pipeline
└── .github/    workflows (ci, audit, triage, deploy) and dependabot
```

## CI/CD

| Workflow | When | What |
|---|---|---|
| `ci.yml` | every PR to main, push to main | Python lint and tests, site types, tests and build, workflow lint, secret scan. The `ci` job is the one required check. |
| `audit.yml` | PRs, weekly, manual | `npm audit` and `pip-audit`. Advisory only, not required. |
| `triage.yml` | daily 06:17 UTC, manual | Classify new issues, publish `triage.json` to the `data` branch, then deploy the site. |
| `deploy.yml` | after triage, push to main touching `site/`, manual | Build the site with the latest data and deploy to GitHub Pages. |

Backfill: run `triage.yml` manually with `since_days` set to 1 to 8 to re-fetch a recent window. Already classified issues are never classified again.

Changing a question: after editing a question in `pipeline/config.py` (for example adding area options), run `triage.yml` manually with `reclassify` set to that question. It re-asks only that question for every issue in the window and overwrites just that answer. Each overwritten answer is stamped with the time and model under `reclassified` on the record, so mixed history stays traceable.

## Run CI locally

`.github/workflows/ci.yml` is the source of truth. This section mirrors it and can drift, so check the workflow if a command here disagrees with it. These commands run repo code (`npm ci` scripts, pytest), so use a trusted checkout, not an unreviewed fork. You need [uv](https://docs.astral.sh/uv/), Node 22 (the version CI uses) and Docker.

Run from the repo root.

**python** (CI runs Python 3.10 and 3.12; pass the version you want to `--python`):

```sh
uv lock --check
uv sync --python 3.12 --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

**site**:

```sh
(cd site && npm ci && npm test && npm run build)
```

**zizmor** (workflow security):

```sh
uvx zizmor@1.32.0 --offline --min-severity medium .github/workflows
```

**actionlint**, **shellcheck** and **secrets** (gitleaks) run in Docker. Copied from `ci.yml`, not verified locally:

```sh
docker run --rm -v "$PWD:/repo" --workdir /repo rhysd/actionlint:1.7.7 -color
docker run --rm -v "$PWD:/mnt" --workdir /mnt koalaman/shellcheck:v0.11.0 scripts/*.sh
docker run --rm -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/repo -v "$PWD:/repo" zricethezav/gitleaks:v8.24.2 git /repo --redact --verbose
```

The gitleaks scan reads the full git history, so use a full clone, not a shallow one.

## Data flow

1. Fetch issues updated since the last run (PRs excluded).
2. Classify only issues not seen before, once each. Stored issues that GitHub no longer returns (deleted or transferred) are removed, unless more than 25 would go at once, which is treated as an incomplete fetch and removes nothing.
3. Keep a rolling 8-day `triage.json` on an orphan `data` branch. The board shows only the 7 complete UTC days in it (`complete_days` in the file), because today and the oldest day are partial.
4. Build and deploy the site to GitHub Pages.
5. MERGE new issues into `abdirahman_portfolio.support_triage_bronze.brz_issue_classifications`.

## Use the data

Every result is already published as one JSON file, `triage.json`. There is no separate export.

- Primary: https://issue-radar.dev/triage.json (served as `application/json`)
- Fallback: https://raw.githubusercontent.com/abdirahman2ali/issue-radar/data/triage.json (served as `text/plain`)

Only the current file is served. History is not kept: the `data` branch is force-pushed on every run, so old versions are not an archive. The file covers a rolling 8-day window. Save your own copy if you need a record.

**Treat every string as untrusted.** `title`, `excerpt`, `labels` and `author` come from public GitHub issues that anyone can file. Do not render them as HTML, do not interpolate them into a shell command, and do not pass them to an LLM that has tool access unless you isolate them first. `title` and `excerpt` are only scrubbed for a few token formats (`sk-ant-`, `gh*_`, `github_pat_`, `sk-`, `AKIA`, `xox*`). They can still contain other secrets or personal data, and nothing here guarantees otherwise.

**Stability.** Fields may be added. Existing field names and types will not change without notice. `tests/test_triage_json_doc.py` checks the field names and types against a synthetic sample file and against a record built by the pipeline code. It does not parse this table, so keep the two in step by hand.

Top level:

| Field | Type | Notes |
|---|---|---|
| `generated_at`, `watermark` | string or null | UTC timestamps; null before the first run |
| `model` | string | Model that classified new issues |
| `complete_days` | `{from, through}`, optional | First and last UTC day (`YYYY-MM-DD`) covered in full. Treat it as optional |
| `issues` | list | One record per issue |

Each record in `issues`:

| Field | Type | Notes |
|---|---|---|
| `repo`, `title`, `excerpt`, `model` | string | `excerpt` is the first 300 characters of the body. Untrusted, see above |
| `number`, `comments` | number | |
| `url` | string | `https://github.com/...` link, or empty |
| `author` | string or null | GitHub login; null for deleted accounts |
| `state` | `"open"` or `"closed"` | |
| `labels` | list of strings | |
| `created_at`, `updated_at`, `classified_at` | string | UTC timestamps |
| `answers` | object | See below |
| `reclassified` | object, optional | Question name to `{at, model}`; present only after a re-ask |

`answers` has `category` and `area` (`{choice, confidence, probabilities}`, where `probabilities` maps each option name to a number), `severity` (`{score, confidence, probabilities}`, keys `"0"` to `"3"`), and four yes/no flags `is_urgent`, `is_regression`, `has_repro`, `needs_info` (`{noul}`, a probability from 0 to 1; the board counts 0.5 or more as yes).

Read-only examples. Pass your own values as arguments or variables, never by building a command or query from strings in the file. Do not pipe a download into a shell.

```sh
curl -fsS --max-time 30 -o triage.json https://issue-radar.dev/triage.json
jq --arg area mcp_tools '[.issues[] | select(.state == "open" and .answers.area.choice == $area)] | length' triage.json
```

```python
import json
from urllib.request import urlopen

area = "mcp_tools"
with urlopen("https://issue-radar.dev/triage.json", timeout=30) as resp:
    data = json.load(resp)
open_in_area = [
    i for i in data["issues"] if i["state"] == "open" and i["answers"]["area"]["choice"] == area
]
print(len(open_in_area))
```

## Secrets

Never commit `.env`. Set these variables locally (shared `.env`) and as GitHub repo secrets:

| Variable | Used by |
|---|---|
| `TYPESAFE_API_KEY` | pipeline (Jev), worker |
| `DATABRICKS_HOST`, `DATABRICKS_TOKEN` | pipeline (warehouse load) |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | worker deploy (phase 2) |
