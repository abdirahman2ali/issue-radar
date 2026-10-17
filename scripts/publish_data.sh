#!/usr/bin/env bash
# Force-push a single triage.json to the orphan `data` branch so history never grows.
# usage: publish_data.sh <triage.json> <remote-url>
# optional env: GIT_AUTH_HEADER (full header value, for example "AUTHORIZATION: basic <b64>")
set -euo pipefail

file="$1"
remote="$2"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

cp "$file" "$work/triage.json"
cd "$work"
git init -q -b data
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add triage.json
git commit -q -m "Update triage data $(date -u +%Y-%m-%dT%H:%MZ)"

if [ -n "${GIT_AUTH_HEADER:-}" ]; then
  git -c "http.extraheader=${GIT_AUTH_HEADER}" push --force "$remote" data
else
  git push --force "$remote" data
fi
