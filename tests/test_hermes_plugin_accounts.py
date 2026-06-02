from __future__ import annotations

from google_health_local_sync import hermes_plugin


class FakeCtx:
    def __init__(self):
        self.tools = {}

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs


def _registered_tools():
    ctx = FakeCtx()
    hermes_plugin.register(ctx)
    return ctx.tools


def test_plugin_status_accepts_person_and_uses_account_data_dir(monkeypatch):
    calls = []

    def fake_run(args, timeout=300):
        calls.append((args, timeout))
        return {"ok": True, "args": args, "timeout": timeout}

    monkeypatch.setattr(hermes_plugin, "_run", fake_run)
    tools = _registered_tools()

    schema_props = tools["google_health_status"]["schema"]["parameters"]["properties"]
    assert "person" in schema_props
    assert "data_dir" in schema_props

    tools["google_health_status"]["handler"]({"person": "sheryl"})

    assert calls == [(["--data-dir", "~/.hermes/google_health_sheryl", "status"], 60)]


def test_plugin_default_person_is_backward_compatible_default_data_dir(monkeypatch):
    calls = []

    def fake_run(args, timeout=300):
        calls.append((args, timeout))
        return {"ok": True, "args": args, "timeout": timeout}

    monkeypatch.setattr(hermes_plugin, "_run", fake_run)
    tools = _registered_tools()

    tools["google_health_fetch_all"]["handler"]({"days": 30, "max_pages": 2})

    assert calls == [(["fetch-all", "--days", "30", "--max-pages", "2"], 600)]


def test_plugin_named_persons_are_not_hardcoded_to_local_usernames(monkeypatch):
    calls = []

    def fake_run(args, timeout=300):
        calls.append((args, timeout))
        return {"ok": True, "args": args, "timeout": timeout}

    monkeypatch.setattr(hermes_plugin, "_run", fake_run)
    tools = _registered_tools()

    tools["google_health_status"]["handler"]({"person": "yc"})
    tools["google_health_status"]["handler"]({"person": "default"})
    tools["google_health_status"]["handler"]({"person": "me"})

    assert calls == [
        (["--data-dir", "~/.hermes/google_health_yc", "status"], 60),
        (["status"], 60),
        (["status"], 60),
    ]


def test_plugin_explicit_data_dir_overrides_person(monkeypatch):
    calls = []

    def fake_run(args, timeout=300):
        calls.append((args, timeout))
        return {"ok": True, "args": args, "timeout": timeout}

    monkeypatch.setattr(hermes_plugin, "_run", fake_run)
    tools = _registered_tools()

    tools["google_health_latest_sleep"]["handler"]({
        "person": "sheryl",
        "data_dir": "~/.hermes/google_health_babu",
        "limit": 7,
    })

    assert calls == [(["--data-dir", "~/.hermes/google_health_babu", "latest-sleep", "--limit", "7"], 60)]


def test_plugin_rejects_unsafe_person_name(monkeypatch):
    calls = []

    def fake_run(args, timeout=300):
        calls.append((args, timeout))
        return {"ok": True}

    monkeypatch.setattr(hermes_plugin, "_run", fake_run)
    tools = _registered_tools()

    result = tools["google_health_status"]["handler"]({"person": "../sheryl"})

    assert "unsafe person" in result
    assert calls == []
