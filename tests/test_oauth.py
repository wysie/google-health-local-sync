from google_health_local_sync.oauth import build_auth_url, expand_scopes, token_payload


def test_build_auth_url_requests_offline_access_and_prompt_consent():
    url = build_auth_url(
        client_id="client-123",
        redirect_uri="https://www.google.com",
        scopes=["https://www.googleapis.com/auth/googlehealth.sleep.readonly"],
        state="yc-test",
    )

    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=client-123" in url
    assert "redirect_uri=https%3A%2F%2Fwww.google.com" in url
    assert "response_type=code" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "state=yc-test" in url
    assert "googlehealth.sleep.readonly" in url


def test_token_payload_uses_authorization_code_grant():
    payload = token_payload(
        code="abc",
        client_id="cid",
        client_secret="secret",
        redirect_uri="https://www.google.com",
    )

    assert payload == {
        "code": "abc",
        "client_id": "cid",
        "client_secret": "secret",
        "redirect_uri": "https://www.google.com",
        "grant_type": "authorization_code",
    }


def test_all_scope_expansion_includes_sensitive_google_health_scopes():
    scopes = expand_scopes("all")

    assert "https://www.googleapis.com/auth/googlehealth.sleep.readonly" in scopes
    assert "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly" in scopes
    assert "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly" in scopes
    assert "https://www.googleapis.com/auth/googlehealth.nutrition.readonly" in scopes
    assert "https://www.googleapis.com/auth/googlehealth.ecg.readonly" in scopes
    assert "https://www.googleapis.com/auth/googlehealth.irn.readonly" in scopes
