from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .oauth import TOKEN_URL, refresh_payload

API_BASE = "https://health.googleapis.com/v4"
TRANSIENT_HTTP_STATUSES = {429, 500, 502, 503, 504}


def _urlopen_json(req: urllib.request.Request, *, timeout: int = 60, max_attempts: int = 4) -> dict[str, Any]:
    last_error = None
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code not in TRANSIENT_HTTP_STATUSES or attempt == max_attempts - 1:
                raise
            time.sleep(2**attempt)
        except urllib.error.URLError as e:
            last_error = e
            if attempt == max_attempts - 1:
                raise
            time.sleep(2**attempt)
    if last_error:
        raise last_error
    raise RuntimeError("unreachable retry state")


def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return _urlopen_json(req, timeout=30)


def post_json(url: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return _urlopen_json(req, timeout=60)


def get_json(url: str, access_token: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
    return _urlopen_json(req, timeout=60)


def refresh_access_token(*, refresh_token: str, client_id: str, client_secret: str) -> dict[str, Any]:
    return post_form(TOKEN_URL, refresh_payload(refresh_token=refresh_token, client_id=client_id, client_secret=client_secret))


def list_data_points(*, access_token: str, data_type: str, page_token: str | None = None, filter_expr: str | None = None) -> dict[str, Any]:
    params = {}
    if page_token:
        params["pageToken"] = page_token
    if filter_expr:
        params["filter"] = filter_expr
    qs = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"{API_BASE}/users/me/dataTypes/{urllib.parse.quote(data_type)}/dataPoints{qs}"
    return get_json(url, access_token)


def _civil_datetime(day: str) -> dict[str, Any]:
    year, month, dom = [int(part) for part in day.split("-")]
    return {"date": {"year": year, "month": month, "day": dom}, "time": {"hours": 0, "minutes": 0, "seconds": 0}}


def daily_rollup_data_points(
    *,
    access_token: str,
    data_type: str,
    start_date: str,
    end_date: str,
    page_token: str | None = None,
    window_size_days: int = 1,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "range": {"start": _civil_datetime(start_date), "end": _civil_datetime(end_date)},
        "windowSizeDays": window_size_days,
    }
    if page_token:
        payload["pageToken"] = page_token
    url = f"{API_BASE}/users/me/dataTypes/{urllib.parse.quote(data_type)}/dataPoints:dailyRollUp"
    return post_json(url, access_token, payload)


def iter_data_points(*, access_token: str, data_type: str, filter_expr: str | None = None):
    token = None
    while True:
        payload = list_data_points(access_token=access_token, data_type=data_type, page_token=token, filter_expr=filter_expr)
        for item in payload.get("dataPoints", []):
            yield item
        token = payload.get("nextPageToken")
        if not token:
            break
