# Google Health Local Sync Hermes plugin

Bundled plugin installed by:

```bash
google-health-local install-hermes-plugin --enable --platform cli --platform whatsapp --platform telegram
```

Toolset:

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

The plugin stores OAuth tokens and synced data only in the configured local data directory. Reference nutrition catalogue data is excluded from default fetch-all unless `include_reference_data` is set explicitly.
