import time

from google_health_local_sync import cli
from google_health_local_sync.storage import GoogleHealthStore


def test_ensure_access_token_refreshes_legacy_token_without_expires_at(tmp_path, monkeypatch):
    store = GoogleHealthStore(tmp_path)
    store.save_token({"access_token": "stale", "refresh_token": "refresh"})
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "env_credentials", lambda: ("cid", "secret", "https://www.google.com"))
    monkeypatch.setattr(
        cli,
        "refresh_access_token",
        lambda *, refresh_token, client_id, client_secret: {"access_token": "fresh", "expires_in": 3600},
    )

    assert cli.ensure_access_token(store) == "fresh"
    saved = store.load_token()
    assert saved["access_token"] == "fresh"
    assert saved["refresh_token"] == "refresh"
    assert saved["expires_at"] > time.time()


def test_ensure_access_token_reuses_unexpired_token(tmp_path, monkeypatch):
    store = GoogleHealthStore(tmp_path)
    store.save_token({"access_token": "fresh", "refresh_token": "refresh", "expires_at": time.time() + 1800})
    called = False

    def unexpected_refresh(**kwargs):
        nonlocal called
        called = True
        return {"access_token": "new"}

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "refresh_access_token", unexpected_refresh)

    assert cli.ensure_access_token(store) == "fresh"
    assert called is False


def test_ensure_access_token_refreshes_nearly_expired_token(tmp_path, monkeypatch):
    store = GoogleHealthStore(tmp_path)
    store.save_token({"access_token": "old", "refresh_token": "refresh", "expires_at": time.time() + 30})
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "env_credentials", lambda: ("cid", "secret", "https://www.google.com"))
    monkeypatch.setattr(
        cli,
        "refresh_access_token",
        lambda *, refresh_token, client_id, client_secret: {"access_token": "new", "expires_in": 3600},
    )

    assert cli.ensure_access_token(store) == "new"
