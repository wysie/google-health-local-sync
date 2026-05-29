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

## Installation

From a local checkout:

```bash
python3 -m pip install -e .
```

From GitHub:

```bash
python3 -m pip install "git+https://github.com/<owner>/google-health-local-sync.git"
```

## Google Cloud setup

Follow Google's Google Health API setup guide:

```text
https://developers.google.com/health/setup
```

Create or enable:

1. Google Health API.
2. OAuth 2.0 Web application client.
3. Authorized redirect URI. This package defaults to:

```text
https://www.google.com
```

4. Test user access if the OAuth app is still in Testing mode.
5. OAuth data access scopes you plan to use.

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
