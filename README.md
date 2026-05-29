# Google Health Local Sync

Local-first sync for Google Health API data. It stores raw Google Health API payloads in a local SQLite database so health dashboards, reports, or agents can parse and re-parse the data without sending records to a hosted backend.

The package also includes an optional Hermes Agent plugin that exposes the same functionality as tools.

## Features

- OAuth helper for Google Health API read-only scopes.
- Local SQLite storage for raw data points.
- Incremental page checkpointing for large API streams.
- Retry/backoff for transient Google API 429/5xx errors.
- Sleep summary parser for recent sleep records.
- Broad personal health sync across sleep, activity, vitals, ECG/IRN, and nutrition log data types.
- Daily rollup support for Google Health types that use rollup endpoints.
- Public nutrition catalogue tables (`food`, `food-measurement-unit`) are excluded from default sync because they are reference data, not personal records. They can be explicitly included when needed.
- Optional Hermes Agent plugin installer.

## Privacy model

This project is local-first:

- OAuth tokens are written only to the configured local data directory.
- Raw health records are written only to local SQLite.
- No hosted service is used by this package.
- Do not commit `.env`, token files, SQLite databases, raw exports, or logs.

Default data directory:

```text
~/.hermes/google_health/
```

Files created there:

```text
token.json
google_health.sqlite
```

## Requirements

- Python 3.9+
- A Google Cloud project with Google Health API enabled
- OAuth 2.0 Web client credentials
- A Google account authorized for the OAuth app

## Quickstart

### Agent-assisted Hermes setup

If you use Hermes Agent or another local coding agent, point it at this repository and ask it to follow [`AGENTS.md`](AGENTS.md). That file is the agent-facing setup playbook: install into Hermes' Python environment, enable the bundled plugin, complete OAuth, run an initial sync, and verify the result without exposing secrets.

Suggested prompt:

```text
Set up google-health-local-sync for my Hermes Agent. Follow AGENTS.md. Install into Hermes' Python environment, enable the plugin, help me complete OAuth, run a bounded initial sync, and verify status.
```

### Manual install

From GitHub:

```bash
python3 -m pip install "git+https://github.com/wysie/google-health-local-sync.git"
```

From a local checkout:

```bash
python3 -m pip install -e .
```

## Google Cloud setup

Follow Google's Google Health API setup guide:

```text
https://developers.google.com/health/setup
```

Create or enable:

1. Google Health API.
2. OAuth consent screen configuration.
3. OAuth 2.0 Web application client.
4. Authorized redirect URI. This package defaults to:

```text
https://www.google.com
```

5. Test user access if the OAuth app is still in Testing mode.
6. OAuth data access scopes you plan to use.

### OAuth consent screen checklist

The OAuth consent screen is a manual Google Cloud Console step. If it is missing or incomplete, Google can block the authorization URL before this CLI ever receives a code.

1. Open Google Cloud Console → APIs & Services → OAuth consent screen.
2. Choose the app audience:
   - `External` is the usual choice for a personal Google account outside a Google Workspace organization.
   - `Internal` only works for users in the same Google Workspace organization.
3. Fill in the required app information:
   - App name, for example `Google Health Local Sync`.
   - User support email.
   - Developer contact email.
4. Add the Google Health read-only scopes you intend to request. For the broad personal sync used by `--scope all`, add the scopes listed below.
5. If the app is in `Testing` publishing status, add every Google account that will authorize the app under Test users. A user who is not listed as a test user cannot complete consent.
6. Create an OAuth client under APIs & Services → Credentials → Create credentials → OAuth client ID:
   - Application type: `Web application`.
   - Authorized redirect URI: `https://www.google.com` unless you pass a different `GOOGLE_HEALTH_REDIRECT_URI` everywhere.
7. Copy the client ID and client secret into local environment variables or your local `.env`. Never commit them.

Notes:

- Google Health scopes are sensitive/restricted. For personal/local use, keeping the OAuth app in Testing mode with explicit test users is usually simplest.
- Testing-mode refresh tokens can expire according to Google's OAuth policies. If sync starts returning `invalid_grant` or authorization errors, re-run the auth URL flow and exchange a new code.
- If you add scopes later, generate a fresh auth URL with `--scope all` and consent again. Old tokens cannot access scopes the user never approved.

Recommended read-only scopes for full personal sync:

```text
https://www.googleapis.com/auth/googlehealth.sleep.readonly
https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
https://www.googleapis.com/auth/googlehealth.nutrition.readonly
https://www.googleapis.com/auth/googlehealth.ecg.readonly
https://www.googleapis.com/auth/googlehealth.irn.readonly
```

## Configure credentials

Put credentials in environment variables or a local `.env` file loaded by your shell or agent runtime:

```bash
GOOGLE_HEALTH_CLIENT_ID="..."
GOOGLE_HEALTH_CLIENT_SECRET="..."
GOOGLE_HEALTH_REDIRECT_URI="https://www.google.com"
```

Never commit real credentials.

## OAuth flow

Generate an authorization URL for all supported read-only scopes:

```bash
google-health-local auth-url --scope all
```

Open the URL, approve access, and copy the `code` value from the redirected URL.

Exchange the code for a local token:

```bash
google-health-local callback --code 'CODE_FROM_REDIRECT'
```

## CLI usage

Check local sync status:

```bash
google-health-local status
```

Fetch one data type:

```bash
google-health-local fetch --data-type sleep --days 7
```

Fetch default personal health data types:

```bash
google-health-local fetch-all --days 30 --max-pages 25
```

Resume checkpointed streams automatically by running the same command again. Disable resume if needed:

```bash
google-health-local fetch-all --days 30 --max-pages 25 --no-resume
```

Fetch only specific data types:

```bash
google-health-local fetch-all --days 365 --data-type sleep --data-type steps --data-type heart-rate
```

Backfill in bounded backwards chunks. This is a safer long-history wrapper around checkpointed `fetch-all`; rerun it to resume interrupted streams:

```bash
google-health-local backfill --chunk-days 30 --max-chunks 12 --max-pages 25
```

Read the latest local summary, including parsed sleep plus latest daily rollups when present:

```bash
google-health-local latest --sleep-limit 3
```

Include public nutrition reference catalogue tables explicitly:

```bash
google-health-local fetch-all --include-reference-data --data-type food --data-type food-measurement-unit
```

Show parsed latest sleep summaries:

```bash
google-health-local latest-sleep --limit 5
```

## Data type notes

Default `fetch-all` is meant for personal health records. It excludes public nutrition catalogue/reference tables:

- `food`
- `food-measurement-unit`

Personal nutrition/hydration logs remain included by default:

- `nutrition-log`
- `hydration-log`

Some Google Health collections only support daily rollups or reject server-side filters. The CLI keeps an internal mapping and falls back to checkpointed list sync where appropriate.

## Hermes Agent plugin

Install and enable the bundled plugin:

```bash
google-health-local install-hermes-plugin --enable --platform cli --platform whatsapp --platform telegram
```

Restart the Hermes gateway or start a fresh Hermes session after enabling the plugin.

Toolset:

```text
google_health
```

Tools:

- `google_health_status`
- `google_health_auth_url`
- `google_health_callback`
- `google_health_fetch`
- `google_health_fetch_all`
- `google_health_backfill`
- `google_health_latest`
- `google_health_latest_sleep`

## Development

Install in editable mode and run tests:

```bash
python3 -m pip install -e . pytest
python3 -m pytest -q
```

## Security

This package handles OAuth tokens and health data. Keep the default local data directory, `.env`, token files, SQLite databases, raw exports, and logs out of git. The repository `.gitignore` covers the common local artifacts, but review your own working tree before publishing.

## License

MIT
