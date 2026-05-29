from __future__ import annotations

import json
import subprocess
import sys

_TOOLSET = "google_health"


def _run(args, timeout=300):
    cmd = [sys.executable, "-m", "google_health_local_sync.cli", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "command": " ".join(cmd)}


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def register(ctx):
    ctx.register_tool(
        name="google_health_status",
        toolset=_TOOLSET,
        schema={"name": "google_health_status", "description": "Check local Google Health sync status.", "parameters": {"type": "object", "properties": {}}},
        handler=lambda args=None, **kw: _json(_run(["status"], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Check Google Health local sync status",
        emoji="🩺",
    )

    ctx.register_tool(
        name="google_health_auth_url",
        toolset=_TOOLSET,
        schema={"name": "google_health_auth_url", "description": "Generate Google Health OAuth URL.", "parameters": {"type": "object", "properties": {"scope": {"type": "array", "items": {"type": "string"}, "default": ["all"]}, "state": {"type": "string", "default": "google-health-local-sync"}}}},
        handler=lambda args=None, **kw: _json(_run(["auth-url"] + sum((["--scope", s] for s in (args or {}).get("scope", ["all"])), []) + ["--state", (args or {}).get("state", "google-health-local-sync")], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Generate Google Health OAuth URL",
        emoji="🔐",
    )

    def callback(args=None, **kw):
        code = (args or {}).get("code")
        if not code:
            return _json({"ok": False, "error": "code is required"})
        return _json(_run(["callback", "--code", code], timeout=120))

    ctx.register_tool(
        name="google_health_callback",
        toolset=_TOOLSET,
        schema={"name": "google_health_callback", "description": "Exchange Google Health OAuth code for local token.", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
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
        return _json(_run(cmd, timeout=300))

    ctx.register_tool(
        name="google_health_fetch",
        toolset=_TOOLSET,
        schema={"name": "google_health_fetch", "description": "Fetch one Google Health API data point collection into local SQLite.", "parameters": {"type": "object", "properties": {"data_type": {"type": "string", "default": "sleep"}, "days": {"type": "integer", "default": 7}, "filter": {"type": "string"}}}},
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
        return _json(_run(cmd, timeout=600))

    ctx.register_tool(
        name="google_health_fetch_all",
        toolset=_TOOLSET,
        schema={"name": "google_health_fetch_all", "description": "Fetch supported personal Google Health API data point collections into local SQLite with checkpoint/resume for large streams and dailyRollUp for summary-only types. Public nutrition catalogue/reference data is excluded by default.", "parameters": {"type": "object", "properties": {"data_type": {"type": "array", "items": {"type": "string"}}, "days": {"type": "integer", "default": 7}, "max_pages": {"type": "integer", "default": 25}, "no_resume": {"type": "boolean", "default": False}, "rollup_only": {"type": "boolean", "default": False}, "include_reference_data": {"type": "boolean", "default": False}}}},
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
        return _json(_run(cmd, timeout=1800))

    ctx.register_tool(
        name="google_health_backfill",
        toolset=_TOOLSET,
        schema={"name": "google_health_backfill", "description": "Backfill Google Health API data backwards with bounded chunks and checkpoint/resume. Public nutrition catalogue/reference data is excluded by default.", "parameters": {"type": "object", "properties": {"data_type": {"type": "array", "items": {"type": "string"}}, "chunk_days": {"type": "integer", "default": 30}, "floor": {"type": "string", "default": "2015-01-01"}, "max_chunks": {"type": "integer"}, "max_pages": {"type": "integer", "default": 25}, "no_resume": {"type": "boolean", "default": False}, "rollup_only": {"type": "boolean", "default": False}, "include_reference_data": {"type": "boolean", "default": False}}}},
        handler=backfill,
        check_fn=lambda: True,
        requires_env=[],
        description="Backfill Google Health data",
        emoji="⏪",
    )

    ctx.register_tool(
        name="google_health_latest",
        toolset=_TOOLSET,
        schema={"name": "google_health_latest", "description": "Read latest local Google Health summary including sleep and latest daily rollups.", "parameters": {"type": "object", "properties": {"sleep_limit": {"type": "integer", "default": 3}}}},
        handler=lambda args=None, **kw: _json(_run(["latest", "--sleep-limit", str(int((args or {}).get("sleep_limit", 3)))], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Read latest Google Health summary",
        emoji="📄",
    )

    ctx.register_tool(
        name="google_health_latest_sleep",
        toolset=_TOOLSET,
        schema={"name": "google_health_latest_sleep", "description": "Read parsed latest Google Health sleep summaries from local SQLite.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "default": 5}}}},
        handler=lambda args=None, **kw: _json(_run(["latest-sleep", "--limit", str(int((args or {}).get("limit", 5)))], timeout=60)),
        check_fn=lambda: True,
        requires_env=[],
        description="Read latest Google Health sleep",
        emoji="😴",
    )
