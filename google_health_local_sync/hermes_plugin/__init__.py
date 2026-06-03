from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_TOOLSET = "google_health"
_PERSON_RE = re.compile(r"^[A-Za-z0-9_-]{1,48}$")
_DEFAULT_PERSONS = {"default", "me"}


def _env_default_person() -> str | None:
    person = (os.getenv("GOOGLE_HEALTH_DEFAULT_PERSON") or "").strip().lower()
    if not person:
        return None
    if not _PERSON_RE.fullmatch(person):
        return None
    return person


def _env_person_aliases() -> dict[str, str]:
    raw = (os.getenv("GOOGLE_HEALTH_PERSON_ALIASES") or "").strip()
    aliases: dict[str, str] = {}
    if not raw:
        return aliases
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        items = parsed.items()
    else:
        items = []
        for part in raw.split(","):
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            items.append((key, value))
    for key, value in items:
        k = str(key).strip().lower()
        v = str(value).strip().lower()
        if _PERSON_RE.fullmatch(k) and _PERSON_RE.fullmatch(v):
            aliases[k] = v
    return aliases


_ACCOUNT_PROPERTIES = {
    "person": {
        "type": "string",
        "description": "Local account/person to use. Omit/default/me uses GOOGLE_HEALTH_DEFAULT_PERSON when set, otherwise the default ~/.hermes/google_health account. Non-default people map to ~/.hermes/google_health_<person>. Optional GOOGLE_HEALTH_PERSON_ALIASES can map nicknames such as babu:sheryl.",
    },
    "data_dir": {
        "type": "string",
        "description": "Explicit Google Health local data directory. Overrides person. Use to keep separate users' token.json and google_health.sqlite files isolated.",
    },
}


def _run(args, timeout=300):
    cmd = [sys.executable, "-m", "google_health_local_sync.cli", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "command": " ".join(cmd)}


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _schema_properties(properties=None):
    merged = dict(_ACCOUNT_PROPERTIES)
    if properties:
        merged.update(properties)
    return merged


def _account_prefix(args=None):
    args = args or {}
    data_dir = args.get("data_dir")
    if data_dir:
        return ["--data-dir", str(data_dir)], None

    person = args.get("person")
    if not person or str(person).lower() in _DEFAULT_PERSONS:
        default_person = _env_default_person()
        if not default_person:
            return [], None
        person = default_person

    person = str(person).lower()
    if not _PERSON_RE.fullmatch(person):
        return [], {"ok": False, "error": f"unsafe person value: {person!r}"}
    person = _env_person_aliases().get(person, person)
    return ["--data-dir", f"~/.hermes/google_health_{person}"], None


def _run_account(args, cmd, timeout=300):
    prefix, error = _account_prefix(args)
    if error:
        return error
    return _run([*prefix, *cmd], timeout=timeout)


def register(ctx):
    ctx.register_tool(
        name="google_health_status",
        toolset=_TOOLSET,
        schema={"name": "google_health_status", "description": "Check local Google Health sync status.", "parameters": {"type": "object", "properties": _schema_properties()}},
        handler=lambda args=None, **kw: _json(_run_account(args, ["status"], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Check Google Health local sync status",
        emoji="🩺",
    )

    ctx.register_tool(
        name="google_health_auth_url",
        toolset=_TOOLSET,
        schema={"name": "google_health_auth_url", "description": "Generate Google Health OAuth URL.", "parameters": {"type": "object", "properties": _schema_properties({"scope": {"type": "array", "items": {"type": "string"}, "default": ["all"]}, "state": {"type": "string", "default": "google-health-local-sync"}})}},
        handler=lambda args=None, **kw: _json(_run_account(args, ["auth-url"] + sum((["--scope", s] for s in (args or {}).get("scope", ["all"])), []) + ["--state", (args or {}).get("state", "google-health-local-sync")], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Generate Google Health OAuth URL",
        emoji="🔐",
    )

    def callback(args=None, **kw):
        code = (args or {}).get("code")
        if not code:
            return _json({"ok": False, "error": "code is required"})
        return _json(_run_account(args, ["callback", "--code", code], timeout=120))

    ctx.register_tool(
        name="google_health_callback",
        toolset=_TOOLSET,
        schema={"name": "google_health_callback", "description": "Exchange Google Health OAuth code for local token.", "parameters": {"type": "object", "properties": _schema_properties({"code": {"type": "string"}}), "required": ["code"]}},
        handler=callback,
        check_fn=lambda: True,
        requires_env=[],
        description="Exchange Google Health OAuth code",
        emoji="✅",
    )

    def fetch(args=None, **kw):
        args = args or {}
        cmd = ["fetch", "--data-type", args.get("data_type", "sleep"), "--days", str(int(args.get("days", 7)))]
        if args.get("filter"):
            cmd += ["--filter", args["filter"]]
        return _json(_run_account(args, cmd, timeout=300))

    ctx.register_tool(
        name="google_health_fetch",
        toolset=_TOOLSET,
        schema={"name": "google_health_fetch", "description": "Fetch one Google Health API data point collection into local SQLite.", "parameters": {"type": "object", "properties": _schema_properties({"data_type": {"type": "string", "default": "sleep"}, "days": {"type": "integer", "default": 7}, "filter": {"type": "string"}})}},
        handler=fetch,
        check_fn=lambda: True,
        requires_env=[],
        description="Fetch Google Health data",
        emoji="📥",
    )

    def fetch_all(args=None, **kw):
        args = args or {}
        cmd = ["fetch-all", "--days", str(int(args.get("days", 7))), "--max-pages", str(int(args.get("max_pages", 25)))]
        if args.get("no_resume"):
            cmd.append("--no-resume")
        if args.get("rollup_only"):
            cmd.append("--rollup-only")
        if args.get("include_reference_data"):
            cmd.append("--include-reference-data")
        for data_type in args.get("data_type", []) or []:
            cmd += ["--data-type", data_type]
        return _json(_run_account(args, cmd, timeout=600))

    ctx.register_tool(
        name="google_health_fetch_all",
        toolset=_TOOLSET,
        schema={"name": "google_health_fetch_all", "description": "Fetch supported personal Google Health API data point collections into local SQLite with checkpoint/resume for large streams and dailyRollUp for summary-only types. Public nutrition catalogue/reference data is excluded by default.", "parameters": {"type": "object", "properties": _schema_properties({"data_type": {"type": "array", "items": {"type": "string"}}, "days": {"type": "integer", "default": 7}, "max_pages": {"type": "integer", "default": 25}, "no_resume": {"type": "boolean", "default": False}, "rollup_only": {"type": "boolean", "default": False}, "include_reference_data": {"type": "boolean", "default": False}})}},
        handler=fetch_all,
        check_fn=lambda: True,
        requires_env=[],
        description="Fetch all Google Health data",
        emoji="📚",
    )

    def backfill(args=None, **kw):
        args = args or {}
        cmd = ["backfill", "--chunk-days", str(int(args.get("chunk_days", 30))), "--floor", args.get("floor", "2015-01-01"), "--max-pages", str(int(args.get("max_pages", 25)))]
        if args.get("max_chunks") is not None:
            cmd += ["--max-chunks", str(int(args["max_chunks"]))]
        if args.get("no_resume"):
            cmd.append("--no-resume")
        if args.get("rollup_only"):
            cmd.append("--rollup-only")
        if args.get("include_reference_data"):
            cmd.append("--include-reference-data")
        for data_type in args.get("data_type", []) or []:
            cmd += ["--data-type", data_type]
        return _json(_run_account(args, cmd, timeout=1800))

    ctx.register_tool(
        name="google_health_backfill",
        toolset=_TOOLSET,
        schema={"name": "google_health_backfill", "description": "Backfill Google Health API data backwards with bounded chunks and checkpoint/resume. Public nutrition catalogue/reference data is excluded by default.", "parameters": {"type": "object", "properties": _schema_properties({"data_type": {"type": "array", "items": {"type": "string"}}, "chunk_days": {"type": "integer", "default": 30}, "floor": {"type": "string", "default": "2015-01-01"}, "max_chunks": {"type": "integer"}, "max_pages": {"type": "integer", "default": 25}, "no_resume": {"type": "boolean", "default": False}, "rollup_only": {"type": "boolean", "default": False}, "include_reference_data": {"type": "boolean", "default": False}})}},
        handler=backfill,
        check_fn=lambda: True,
        requires_env=[],
        description="Backfill Google Health data",
        emoji="⏪",
    )

    ctx.register_tool(
        name="google_health_latest",
        toolset=_TOOLSET,
        schema={"name": "google_health_latest", "description": "Read latest local Google Health summary including sleep and latest daily rollups.", "parameters": {"type": "object", "properties": _schema_properties({"sleep_limit": {"type": "integer", "default": 3}})}},
        handler=lambda args=None, **kw: _json(_run_account(args, ["latest", "--sleep-limit", str(int((args or {}).get("sleep_limit", 3)))], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Read latest Google Health summary",
        emoji="📄",
    )

    ctx.register_tool(
        name="google_health_latest_sleep",
        toolset=_TOOLSET,
        schema={"name": "google_health_latest_sleep", "description": "Read parsed latest Google Health sleep summaries from local SQLite.", "parameters": {"type": "object", "properties": _schema_properties({"limit": {"type": "integer", "default": 5}})}},
        handler=lambda args=None, **kw: _json(_run_account(args, ["latest-sleep", "--limit", str(int((args or {}).get("limit", 5)))], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Read latest Google Health sleep",
        emoji="😴",
    )
