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

## Data flow

1. Fetch issues updated since the last run (PRs excluded).
2. Classify only issues not seen before, once each. Stored issues that GitHub no longer returns (deleted or transferred) are removed, unless more than 25 would go at once, which is treated as an incomplete fetch and removes nothing.
3. Keep a rolling 8-day `triage.json` on an orphan `data` branch. The board starts at the first complete day (`complete_days.from`, since the oldest day is partial) and runs through the day of the last run, which is still filling up.
4. Build and deploy the site to GitHub Pages.
5. MERGE new issues into `abdirahman_portfolio.support_triage_bronze.brz_issue_classifications`.

## Secrets

Never commit `.env`. Set these variables locally (shared `.env`) and as GitHub repo secrets:

| Variable | Used by |
|---|---|
| `TYPESAFE_API_KEY` | pipeline (Jev), worker |
| `DATABRICKS_HOST`, `DATABRICKS_TOKEN` | pipeline (warehouse load) |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | worker deploy (phase 2) |
