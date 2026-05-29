from __future__ import annotations

import argparse
import json
import os
import urllib.error
from datetime import date, datetime, timedelta, timezone

from .client import daily_rollup_data_points, iter_data_points, list_data_points, post_form, refresh_access_token
from .data_types import DAILY_ROLLUP_DATA_TYPES, DEFAULT_SYNC_DATA_TYPES, GOOGLE_HEALTH_DATA_TYPES, INTERVAL_FILTER_MEMBERS, ROLLUP_14_DAY_MAX_TYPES
from .oauth import TOKEN_URL, build_auth_url, env_credentials, expand_scopes, token_payload
from .sleep import seconds_to_hm, summarize_sleep_datapoint
from .hermes_install import install_hermes_plugin
from .storage import GoogleHealthStore


def load_dotenv(path: str = "~/.hermes/.env") -> None:
    p = os.path.expanduser(path)
    if not os.path.exists(p):
        return
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def cmd_auth_url(args) -> None:
    load_dotenv()
    client_id = args.client_id or os.environ.get("GOOGLE_HEALTH_CLIENT_ID")
    if not client_id:
        raise SystemExit("Set GOOGLE_HEALTH_CLIENT_ID or pass --client-id")
    redirect_uri = args.redirect_uri or os.environ.get("GOOGLE_HEALTH_REDIRECT_URI", "https://www.google.com")
    print(build_auth_url(client_id=client_id, redirect_uri=redirect_uri, scopes=expand_scopes(args.scope), state=args.state))


def cmd_callback(args) -> None:
    load_dotenv()
    client_id, client_secret, redirect_uri = env_credentials()
    token = post_form(TOKEN_URL, token_payload(code=args.code, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri))
    store = GoogleHealthStore(args.data_dir)
    store.save_token(token)
    print(json.dumps({"saved": str(store.token_path), "scope": token.get("scope"), "expires_in": token.get("expires_in"), "has_refresh_token": bool(token.get("refresh_token"))}, indent=2))


def ensure_access_token(store: GoogleHealthStore) -> str:
    load_dotenv()
    token = store.load_token()
    if token.get("access_token"):
        return token["access_token"]
    if not token.get("refresh_token"):
        raise SystemExit("No access_token or refresh_token. Run callback again with prompt=consent.")
    client_id, client_secret, _ = env_credentials()
    refreshed = refresh_access_token(refresh_token=token["refresh_token"], client_id=client_id, client_secret=client_secret)
    token.update(refreshed)
    store.save_token(token)
    return token["access_token"]


def _local_start_cutoff(days: int | None):
    return datetime.now(timezone.utc) - timedelta(days=days) if days else None


def _server_filter_for(data_type: str, cutoff) -> str | None:
    if not cutoff:
        return None
    member = INTERVAL_FILTER_MEMBERS.get(data_type)
    if not member:
        return None
    start = cutoff.strftime("%Y-%m-%dT00:00:00Z")
    return f'{member} >= "{start}"'


def _datapoint_start(data_type: str, dp: dict):
    payload = dp.get(data_type.replace("-", "_")) or dp.get(data_type) or {}
    interval = payload.get("interval") or {}
    return interval.get("startTime") or payload.get("startTime")


def _is_before_cutoff(data_type: str, dp: dict, cutoff) -> bool:
    if not cutoff:
        return False
    started = _datapoint_start(data_type, dp)
    if not started:
        return False
    try:
        dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        return dt < cutoff
    except Exception:
        return False


def _date_chunks(start: date, end: date, chunk_days: int):
    cur = start
    while cur < end:
        nxt = min(end, cur + timedelta(days=chunk_days))
        yield cur, nxt
        cur = nxt


def _fetch_list_type(*, store: GoogleHealthStore, access_token: str, data_type: str, cutoff, max_pages: int, resume: bool) -> dict:
    count = inserted = pages = 0
    filter_expr = _server_filter_for(data_type, cutoff)
    state_key = f"list:{data_type}:{filter_expr or 'unfiltered'}"
    state = store.get_sync_state(state_key) if resume else None
    token = (state or {}).get("page_token")
    while True:
        payload = list_data_points(access_token=access_token, data_type=data_type, page_token=token, filter_expr=filter_expr)
        pages += 1
        for dp in payload.get("dataPoints", []):
            count += 1
            if _is_before_cutoff(data_type, dp, cutoff):
                continue
            inserted += int(store.upsert_datapoint(data_type=data_type, data_point=dp))
        token = payload.get("nextPageToken")
        if token:
            store.set_sync_state(state_key, {"page_token": token, "data_type": data_type, "filter": filter_expr, "pages_done": pages})
        else:
            store.clear_sync_state(state_key)
            break
        if pages >= max_pages:
            break
    return {"mode": "list", "seen": count, "inserted": inserted, "pages": pages, "checkpointed": bool(token), "state_key": state_key if token else None}


def _fetch_rollup_type(*, store: GoogleHealthStore, access_token: str, data_type: str, days: int, max_pages: int, resume: bool) -> dict:
    today = date.today()
    start = today - timedelta(days=days)
    chunk_days = 14 if data_type in ROLLUP_14_DAY_MAX_TYPES else 90
    count = inserted = pages = 0
    last_checkpoint = None
    for chunk_start, chunk_end in _date_chunks(start, today, chunk_days):
        state_key = f"dailyRollUp:{data_type}:{chunk_start.isoformat()}:{chunk_end.isoformat()}"
        state = store.get_sync_state(state_key) if resume else None
        token = (state or {}).get("page_token")
        while True:
            payload = daily_rollup_data_points(
                access_token=access_token,
                data_type=data_type,
                start_date=chunk_start.isoformat(),
                end_date=chunk_end.isoformat(),
                page_token=token,
            )
            pages += 1
            for rp in payload.get("rollupDataPoints", []):
                count += 1
                inserted += int(store.upsert_rollup(data_type=data_type, rollup_point=rp))
            token = payload.get("nextPageToken")
            if token:
                store.set_sync_state(state_key, {"page_token": token, "data_type": data_type, "start": chunk_start.isoformat(), "end": chunk_end.isoformat(), "pages_done": pages})
                last_checkpoint = state_key
            else:
                store.clear_sync_state(state_key)
                last_checkpoint = None
                break
            if pages >= max_pages:
                return {"mode": "dailyRollUp", "seen": count, "inserted": inserted, "pages": pages, "checkpointed": True, "state_key": last_checkpoint}
    return {"mode": "dailyRollUp", "seen": count, "inserted": inserted, "pages": pages, "checkpointed": False, "state_key": None}


def cmd_fetch(args) -> None:
    store = GoogleHealthStore(args.data_dir)
    access_token = ensure_access_token(store)
    filter_expr = args.filter
    cutoff = _local_start_cutoff(args.days) if not filter_expr else None
    count = inserted = 0
    for dp in iter_data_points(access_token=access_token, data_type=args.data_type, filter_expr=filter_expr):
        count += 1
        if _is_before_cutoff(args.data_type, dp, cutoff):
            continue
        inserted += int(store.upsert_datapoint(data_type=args.data_type, data_point=dp))
    print(json.dumps({"data_type": args.data_type, "seen": count, "inserted": inserted, "db": str(store.db_path)}, indent=2))


def cmd_fetch_all(args) -> None:
    store = GoogleHealthStore(args.data_dir)
    access_token = ensure_access_token(store)
    default_data_types = GOOGLE_HEALTH_DATA_TYPES if args.include_reference_data else DEFAULT_SYNC_DATA_TYPES
    data_types = args.data_type or list(default_data_types)
    cutoff = _local_start_cutoff(args.days)
    results = []
    total_seen = total_inserted = 0
    for data_type in data_types:
        error = None
        result = {"mode": None, "seen": 0, "inserted": 0, "pages": 0, "checkpointed": False, "state_key": None}
        try:
            if data_type in DAILY_ROLLUP_DATA_TYPES or args.rollup_only:
                result = _fetch_rollup_type(store=store, access_token=access_token, data_type=data_type, days=args.days, max_pages=args.max_pages, resume=not args.no_resume)
            else:
                result = _fetch_list_type(store=store, access_token=access_token, data_type=data_type, cutoff=cutoff, max_pages=args.max_pages, resume=not args.no_resume)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:1000]
            error = {"status": e.code, "reason": e.reason, "body": body}
        except Exception as e:
            error = {"type": type(e).__name__, "message": str(e)}
        total_seen += int(result.get("seen") or 0)
        total_inserted += int(result.get("inserted") or 0)
        results.append({"data_type": data_type, **result, "error": error})
    print(json.dumps({"ok": all(not r["error"] for r in results), "total_seen": total_seen, "total_inserted": total_inserted, "db": str(store.db_path), "results": results}, indent=2, ensure_ascii=False))


def cmd_latest_sleep(args) -> None:
    store = GoogleHealthStore(args.data_dir)
    rows = store.list_datapoints("sleep", limit=args.limit)
    out = []
    for row in rows:
        summary = summarize_sleep_datapoint(json.loads(row["raw_json"]))
        out.append({
            **summary,
            "time_in_bed": seconds_to_hm(summary["time_in_bed_seconds"]),
            "display_sleep": seconds_to_hm(summary["display_sleep_seconds"]),
            "awake": seconds_to_hm(summary["awake_seconds"]),
            "restless": seconds_to_hm(summary["restless_seconds"]),
        })
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_status(args) -> None:
    store = GoogleHealthStore(args.data_dir)
    token_exists = store.token_path.exists()
    db_exists = store.db_path.exists()
    counts_by_data_type = store.counts_by_data_type() if db_exists else {}
    print(json.dumps({
        "ok": True,
        "data_dir": str(store.data_dir),
        "token_path": str(store.token_path),
        "token_exists": token_exists,
        "db_path": str(store.db_path),
        "db_exists": db_exists,
        "sleep_records": counts_by_data_type.get("sleep", 0),
        "counts_by_data_type": counts_by_data_type,
    }, indent=2))


def cmd_install_hermes_plugin(args) -> None:
    result = install_hermes_plugin(hermes_home=args.hermes_home, enable=args.enable, platforms=args.platform)
    print(json.dumps(result, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="google-health-local")
    p.add_argument("--data-dir", default="~/.hermes/google_health")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("auth-url")
    a.add_argument("--client-id")
    a.add_argument("--redirect-uri")
    a.add_argument("--scope", action="append", default=["all"])
    a.add_argument("--state", default="google-health-local-sync")
    a.set_defaults(func=cmd_auth_url)

    c = sub.add_parser("callback")
    c.add_argument("--code", required=True)
    c.set_defaults(func=cmd_callback)

    f = sub.add_parser("fetch")
    f.add_argument("--data-type", default="sleep")
    f.add_argument("--days", type=int, default=7)
    f.add_argument("--filter")
    f.set_defaults(func=cmd_fetch)

    fa = sub.add_parser("fetch-all")
    fa.add_argument("--data-type", action="append", default=[])
    fa.add_argument("--days", type=int, default=7)
    fa.add_argument("--max-pages", type=int, default=25)
    fa.add_argument("--no-resume", action="store_true")
    fa.add_argument("--rollup-only", action="store_true")
    fa.add_argument("--include-reference-data", action="store_true", help="Include public Google/Fitbit nutrition catalogue tables such as food and food-measurement-unit")
    fa.set_defaults(func=cmd_fetch_all)

    l = sub.add_parser("latest-sleep")
    l.add_argument("--limit", type=int, default=5)
    l.set_defaults(func=cmd_latest_sleep)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)

    i = sub.add_parser("install-hermes-plugin")
    i.add_argument("--hermes-home", default=None)
    i.add_argument("--enable", action="store_true")
    i.add_argument("--platform", action="append", default=[])
    i.set_defaults(func=cmd_install_hermes_plugin)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
