# Repair agent setup

Files: `../workflows/repair.yml` (fix and open PR), `../workflows/verify.yml` (re-run, check
production, revert), `repair-prompt.md` (the agent's instructions), `scripts/check_production.py`.

One-time setup (the agent stays off until step 4):

1. Create a GitHub App for this repo only, with Contents, Pull requests and Issues set to
   read and write. Install it on this repo. Add repo variable `AGENT_APP_ID` and secret
   `AGENT_APP_PRIVATE_KEY`. An App token is needed so the PRs it opens trigger CI.
2. Add secret `ANTHROPIC_API_KEY`.
3. Repo settings: enable "Allow auto-merge". Keep `ci` as the required check.
4. Add repo variable `AGENT_ENABLED` = `true`. Set it to anything else to stop the agent.

Dry run: with the variable on, re-run a failed workflow run, or run `python
scripts/check_production.py` locally.

The agent can not edit `.github/`, `.claude/`, `CLAUDE.md` or the production check, can not
delete tests, and is limited to 2 PRs per workflow per 7 days.
