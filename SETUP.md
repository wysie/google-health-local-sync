# Installation and setup

## Agent-assisted Hermes setup

For Hermes Agent users, the repository includes [`AGENTS.md`](AGENTS.md). A user can point Hermes at this repository and ask it to set everything up.

Suggested prompt:

```text
Set up google-health-local-sync for my Hermes Agent. Follow AGENTS.md. Install into Hermes' Python environment, enable the plugin for cli/whatsapp/telegram unless I say otherwise, configure ~/.hermes/.env without exposing secrets, generate the auth URL, exchange my OAuth code, run a bounded initial sync, and verify status.
```

The rest of this document is the manual version of the same flow.

## 1. Install

From GitHub:

```bash
python3 -m pip install "git+https://github.com/<owner>/google-health-local-sync.git"
```

For local development:

```bash
python3 -m pip install -e /path/to/google-health-local-sync
```

If you want the package installed inside a specific agent or application virtualenv, use that virtualenv's Python executable:

```bash
/path/to/venv/bin/python -m pip install -e /path/to/google-health-local-sync
```

## 2. Google Cloud OAuth setup

Follow Google's official setup guide:

```text
https://developers.google.com/health/setup
```

Create or configure:

1. A Google Cloud project.
2. Google Health API enabled for the project.
3. An OAuth 2.0 Web application client.
4. Authorized redirect URI:

```text
https://www.google.com
```

5. Test users, if your OAuth consent screen is in Testing mode.
6. OAuth data access scopes you plan to use.

Recommended read-only scopes for broad personal sync:

```text
https://www.googleapis.com/auth/googlehealth.sleep.readonly
https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly
https://www.googleapis.com/auth/googlehealth.nutrition.readonly
https://www.googleapis.com/auth/googlehealth.ecg.readonly
https://www.googleapis.com/auth/googlehealth.irn.readonly
```

## 3. Configure credentials

Set credentials in your shell or a local `.env` file that is not committed:

```bash
export GOOGLE_HEALTH_CLIENT_ID="..."
export GOOGLE_HEALTH_CLIENT_SECRET="..."
export GOOGLE_HEALTH_REDIRECT_URI="https://www.google.com"
```

When running with Hermes Agent, this package also loads `~/.hermes/.env` by default.

## 4. Authorize

Generate an authorization URL for all supported read-only scopes:

```bash
google-health-local auth-url --scope all
```

Open the URL, approve access, and copy the `code=...` value from the redirected URL.

Exchange the code locally:

```bash
google-health-local callback --code 'CODE_FROM_REDIRECT'
```

The token is saved under the configured data directory. The default is:

```text
~/.hermes/google_health/token.json
```

## 5. Sync data

Fetch one data type:

```bash
google-health-local fetch --data-type sleep --days 7
```

Fetch default personal data types:

```bash
google-health-local fetch-all --days 30 --max-pages 25
```

Resume a checkpointed fetch by running the same command again.

Reference nutrition catalogue tables are excluded by default. Include them only if you explicitly need Google/Fitbit public food lookup records:

```bash
google-health-local fetch-all --include-reference-data --data-type food --data-type food-measurement-unit
```

## 6. Inspect data

```bash
google-health-local latest-sleep
google-health-local status
```

## 7. Optional Hermes Agent plugin

Install and enable the bundled plugin:

```bash
google-health-local install-hermes-plugin --enable --platform cli --platform whatsapp --platform telegram
```

Restart the gateway or start a fresh session after enabling the plugin.

Plugin toolset:

```text
google_health
```

Tools:

```text
google_health_status
google_health_auth_url
google_health_callback
google_health_fetch
google_health_fetch_all
google_health_latest_sleep
```

## Data files

Default local files:

```text
~/.hermes/google_health/token.json
~/.hermes/google_health/google_health.sqlite
```

Never commit tokens, SQLite databases, `.env` files, raw exports, or logs.
