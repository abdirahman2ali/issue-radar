# issue-radar

A daily triage board for GitHub issues, classified by Jev (TypeSafe AI's System One model).

Once a day a GitHub Actions job pulls new issues from `anthropics/claude-code`, classifies each one with Jev (category, area, severity, urgency, regression, repro, needs info), publishes an interactive board to GitHub Pages, and incrementally loads the results into Databricks.

## Status

Scaffold only. The pipeline, site, and workflow are not built yet.

## Planned layout

```
issue-radar/
├── pipeline/   Python: fetch issues, classify with Jev, merge, load to Databricks
├── site/       Vite + React + TypeScript board (filters, charts, detail drawer)
├── worker/     Cloudflare Worker for the live try-it box (phase 2)
└── .github/    daily workflow, Pages deploy
```

## Data flow

1. Fetch issues updated since the last run (PRs excluded).
2. Classify only issues not seen before, once each.
3. Keep a rolling 7-day `triage.json` on an orphan `data` branch.
4. Build and deploy the site to GitHub Pages.
5. MERGE new issues into `abdirahman_portfolio.support_triage_bronze.brz_issue_classifications`.

## Secrets

Never commit `.env`. Set these variables locally (shared `.env`) and as GitHub repo secrets:

| Variable | Used by |
|---|---|
| `TYPESAFE_API_KEY` | pipeline (Jev), worker |
| `DATABRICKS_HOST`, `DATABRICKS_TOKEN` | pipeline (warehouse load) |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | worker deploy (phase 2) |
