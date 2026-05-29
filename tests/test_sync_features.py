from google_health_local_sync.client import daily_rollup_data_points
from google_health_local_sync.cli import _server_filter_for
from google_health_local_sync.storage import GoogleHealthStore


def test_store_persists_sync_state_checkpoint(tmp_path):
    store = GoogleHealthStore(tmp_path)

    store.set_sync_state("list:heart-rate", {"page_token": "abc", "pages_done": 3})

    assert store.get_sync_state("list:heart-rate") == {"page_token": "abc", "pages_done": 3}

    store.clear_sync_state("list:heart-rate")
    assert store.get_sync_state("list:heart-rate") is None


def test_store_upserts_daily_rollup_points(tmp_path):
    store = GoogleHealthStore(tmp_path)
    rollup = {
        "civilStartTime": {"date": {"year": 2026, "month": 5, "day": 28}, "time": {}},
        "civilEndTime": {"date": {"year": 2026, "month": 5, "day": 29}, "time": {}},
        "totalCalories": {"kcalSum": 1723.9},
    }

    assert store.upsert_rollup(data_type="total-calories", rollup_point=rollup) is True
    assert store.upsert_rollup(data_type="total-calories", rollup_point=rollup) is False

    rows = store.list_datapoints("total-calories:daily-rollup")
    assert len(rows) == 1
    assert rows[0]["start_time"] == "2026-05-28"
    assert rows[0]["end_time"] == "2026-05-29"
    assert "totalCalories" in rows[0]["raw_json"]


def test_daily_rollup_posts_civil_range(monkeypatch):
    captured = {}

    def fake_post_json(url, access_token, payload):
        captured["url"] = url
        captured["access_token"] = access_token
        captured["payload"] = payload
        return {"rollupDataPoints": []}

    monkeypatch.setattr("google_health_local_sync.client.post_json", fake_post_json)

    out = daily_rollup_data_points(
        access_token="tok",
        data_type="total-calories",
        start_date="2026-05-22",
        end_date="2026-05-29",
        page_token="next",
    )

    assert out == {"rollupDataPoints": []}
    assert captured["url"].endswith("/users/me/dataTypes/total-calories/dataPoints:dailyRollUp")
    assert captured["access_token"] == "tok"
    assert captured["payload"]["range"]["start"]["date"] == {"year": 2026, "month": 5, "day": 22}
    assert captured["payload"]["range"]["end"]["date"] == {"year": 2026, "month": 5, "day": 29}
    assert captured["payload"]["windowSizeDays"] == 1
    assert captured["payload"]["pageToken"] == "next"


def test_known_session_and_vo2_types_do_not_get_invalid_interval_filters():
    for data_type in ("exercise", "run-vo2-max", "vo2-max"):
        assert _server_filter_for(data_type, object()) is None
