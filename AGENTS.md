# Agent-assisted setup guide

This file is for Hermes Agent or another local coding agent. A user should be able to point an agent at this repository and say: "Set this up for me." Follow these steps and do not guess credentials.

## Goal

Install `google-health-local-sync` into the user's Hermes Agent Python environment, enable the bundled Hermes plugin, guide the user through Google Health OAuth, run an initial local sync, and verify that the plugin tools work.

## Safety rules

- Do not print, commit, upload, or summarize OAuth client secrets, OAuth codes, refresh tokens, access tokens, SQLite databases, raw health exports, or `.env` files.
- Keep all Google Health data local. Default data directory: `~/.hermes/google_health/`.
- Never commit files under `~/.hermes/google_health/`.
- Do not include public nutrition reference catalogue data (`food`, `food-measurement-unit`) unless the user explicitly asks for it. Default personal sync excludes those reference tables.
- If credentials are missing, ask the user for the Google Health OAuth client ID and client secret, or ask them to add those values to `~/.hermes/.env`. Do not invent placeholders and proceed as if authenticated.
- If a command would overwrite an existing token or database, state exactly what file is affected before doing it.

## Prerequisites

The user needs a Google Cloud OAuth client with Google Health API enabled.

Google setup docs:

```text
https://developers.google.com/health/setup
```

OAuth client type: Web application.

Authorized redirect URI:

```text
https://www.google.com
```

Recommended read-only scopes for broad personal health sync:

```text
https://www.googleapis.com/auth/googlehealth.sleep.readonly
https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
https://www.googleapis.com/auth/googlehealth.nutrition.readonly
https://www.googleapis.com/auth/googlehealth.ecg.readonly
https://www.googleapis.com/auth/googlehealth.irn.readonly
```

## Quick agent prompt

If the user pastes this file or points you at this repo, this is the intended task:

```text
Install google-health-local-sync into Hermes Agent's own Python environment, run the bundled plugin installer with --enable for cli/whatsapp/telegram unless I specify different platforms, configure GOOGLE_HEALTH_* variables in ~/.hermes/.env without revealing secrets, generate the Google Health auth URL, exchange the OAuth code I provide, run a bounded initial fetch-all or backfill, verify status/latest/latest-sleep, and tell me what passed.
```

## 1. Locate Hermes and its Python environment

Prefer Hermes' own virtualenv when it exists:

```bash
if [ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]; then
  HERMES_PYTHON="$HOME/.hermes/hermes-agent/venv/bin/python"
elif command -v hermes >/dev/null 2>&1; then
  HERMES_PYTHON="$(python3 - <<'PY'
import os, shutil, subprocess, sys
hermes = shutil.which('hermes')
if not hermes:
    raise SystemExit(1)
# Best effort fallback: use current Python if Hermes venv is not discoverable.
print(sys.executable)
PY
)"
else
  HERMES_PYTHON="$(command -v python3)"
fi
printf 'Using Python: %s\n' "$HERMES_PYTHON"
```

If the user has a custom Hermes profile or custom installation path, use the Python executable for that Hermes runtime.

## 2. Install this package into Hermes' Python environment

From a local checkout:

```bash
"$HERMES_PYTHON" -m pip install -e /path/to/google-health-local-sync
```

From GitHub:

```bash
"$HERMES_PYTHON" -m pip install "git+https://github.com/wysie/google-health-local-sync.git"
```

Verify the CLI is importable:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli --help
```

## 3. Configure credentials in `~/.hermes/.env`

Required variables:

```bash
GOOGLE_HEALTH_CLIENT_ID="..."
GOOGLE_HEALTH_CLIENT_SECRET="..."
GOOGLE_HEALTH_REDIRECT_URI="https://www.google.com"
```

Optional data directory override:

```bash
GOOGLE_HEALTH_DATA_DIR="$HOME/.hermes/google_health"
```

Agent behaviour:

1. Check whether `~/.hermes/.env` exists.
2. If variables are missing, ask the user for the missing values or ask them to edit the file manually.
3. When writing values, append/update only the `GOOGLE_HEALTH_*` lines.
4. Do not print the secret value after writing it.

## 4. Install and enable the bundled Hermes Agent plugin

Install into Hermes' plugin directory and enable the `google_health` toolset.

Default platforms match the common gateway setup:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli install-hermes-plugin \
  --enable \
  --platform cli \
  --platform whatsapp \
  --platform telegram
```

If the user only wants CLI, use:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli install-hermes-plugin --enable --platform cli
```

After installing, restart Hermes gateway or start a fresh Hermes CLI/session before expecting new tools to appear.

Useful restart commands when available:

```bash
hermes gateway restart
```

or ask the user to send `/restart` from their gateway chat.

## 5. Authorize Google Health

Generate an authorization URL for all supported read-only scopes:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli auth-url --scope all
```

Ask the user to open the URL, approve access, and copy the `code=...` query parameter from the final redirected URL.

Exchange the code locally:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli callback --code 'PASTE_CODE_HERE'
```

Expected local token path:

```text
~/.hermes/google_health/token.json
```

## 6. Run an initial bounded sync

Start with a bounded personal sync so setup verifies quickly:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli fetch-all --days 30 --max-pages 25
```

For a smoke test, use fewer pages:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli fetch-all --days 7 --max-pages 5
```

For longer history, use the bounded backfill wrapper and rerun it to resume interrupted streams:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli backfill --chunk-days 30 --max-chunks 12 --max-pages 25
```

Resume checkpointed streams by rerunning the same command. Do not use `--include-reference-data` unless the user explicitly requests public nutrition catalogue/reference rows.

## 7. Verify setup

Run:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli status
"$HERMES_PYTHON" -m google_health_local_sync.cli latest --sleep-limit 3
"$HERMES_PYTHON" -m google_health_local_sync.cli latest-sleep --limit 5
```

If running inside Hermes after a restart, verify plugin tools:

```text
google_health_status
google_health_auth_url
google_health_callback
google_health_fetch
google_health_fetch_all
google_health_backfill
google_health_latest
google_health_latest_sleep
```

A good final report should include:

- package installed successfully
- plugin installed and enabled platforms
- token saved locally
- initial fetch command and result
- status summary
- latest sleep summary if available
- any failed data types and their exact API errors

## 8. Optional local daily refresh

Do not schedule background jobs without user consent. If the user wants the local cache warmed automatically, create a local-only daily Hermes cron job or system cron that runs:

```bash
"$HERMES_PYTHON" -m google_health_local_sync.cli fetch-all --days 7 --max-pages 25
```

Recommended delivery for Hermes cron: local only, no chat spam.

## Troubleshooting

### Missing OAuth scope / 403

Generate a fresh auth URL with `--scope all`, re-consent, and exchange the new code. A token minted with fewer scopes cannot access broader data types.

### Invalid data type filter / 400

Do not hand-write filters for known data types unless necessary. The CLI contains mappings for server-side filters, local filtering, and daily rollup-only data types.

### Long sync times

Use smaller bounded chunks:

```bash
google-health-local fetch-all --days 30 --max-pages 10
```

Then rerun to resume from checkpoints.

### Plugin installed but tools missing

Restart Hermes gateway or start a new Hermes session. Tool and plugin changes do not reliably appear mid-session.

### Data locations

```text
~/.hermes/google_health/token.json
~/.hermes/google_health/google_health.sqlite
```

Keep these local and out of git.
