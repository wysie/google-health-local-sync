from __future__ import annotations

import os
from urllib.parse import urlencode

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REDIRECT_URI = "https://www.google.com"
SCOPE_MAP = {
    "sleep": "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
    "activity": "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "fitness": "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "health": "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "metrics": "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "measurements": "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "nutrition": "https://www.googleapis.com/auth/googlehealth.nutrition.readonly",
    "food": "https://www.googleapis.com/auth/googlehealth.nutrition.readonly",
    "ecg": "https://www.googleapis.com/auth/googlehealth.ecg.readonly",
    "electrocardiogram": "https://www.googleapis.com/auth/googlehealth.ecg.readonly",
    "irn": "https://www.googleapis.com/auth/googlehealth.irn.readonly",
    "irregular-rhythm-notification": "https://www.googleapis.com/auth/googlehealth.irn.readonly",
}
ALL_SCOPE_KEYS = ("sleep", "activity", "health", "nutrition", "ecg", "irn")


def expand_scopes(scopes: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if scopes is None:
        parts = ["all"]
    elif isinstance(scopes, str):
        parts = [p.strip() for p in scopes.replace(",", " ").split() if p.strip()]
    else:
        parts = list(scopes)

    if not parts:
        parts = ["all"]

    expanded: list[str] = []
    for item in parts:
        if item == "all":
            expanded.extend(SCOPE_MAP[k] for k in ALL_SCOPE_KEYS)
        else:
            expanded.append(SCOPE_MAP.get(item, item))

    out: list[str] = []
    seen: set[str] = set()
    for item in expanded:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_auth_url(
    *,
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scopes: list[str] | tuple[str, ...] | str | None = None,
    state: str | None = None,
    prompt_consent: bool = True,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "scope": " ".join(expand_scopes(scopes)),
    }
    if prompt_consent:
        params["prompt"] = "consent"
    if state:
        params["state"] = state
    return f"{AUTH_URL}?{urlencode(params)}"


def token_payload(*, code: str, client_id: str, client_secret: str, redirect_uri: str = DEFAULT_REDIRECT_URI) -> dict[str, str]:
    return {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }


def refresh_payload(*, refresh_token: str, client_id: str, client_secret: str) -> dict[str, str]:
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }


def env_credentials() -> tuple[str, str, str]:
    client_id = os.environ.get("GOOGLE_HEALTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_HEALTH_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_HEALTH_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    if not client_id or not client_secret:
        raise RuntimeError("Set GOOGLE_HEALTH_CLIENT_ID and GOOGLE_HEALTH_CLIENT_SECRET")
    return client_id, client_secret, redirect_uri
