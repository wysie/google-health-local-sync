import json
from datetime import date

from google_health_local_sync.cli import _backfill_windows, build_latest_summary
from google_health_local_sync.storage import GoogleHealthStore


def test_backfill_windows_walk_backward_from_today_to_floor():
    windows = list(_backfill_windows(today=date(2026, 5, 29), floor=date(2026, 4, 1), chunk_days=30, max_chunks=3))

    assert windows == [
        (date(2026, 4, 29), date(2026, 5, 29)),
        (date(2026, 4, 1), date(2026, 4, 29)),
    ]


def test_latest_summary_includes_sleep_and_daily_rollup_counts(tmp_path):
    store = GoogleHealthStore(tmp_path)
    store.upsert_datapoint(
        data_type="sleep",
        data_point={
            "name": "users/me/dataTypes/sleep/dataPoints/s1",
            "sleep": {
                "type": "CLASSIC",
                "interval": {"startTime": "2026-05-28T17:00:00Z", "endTime": "2026-05-28T23:00:00Z"},
                "sleepStages": [
                    {"startTime": "2026-05-28T17:00:00Z", "endTime": "2026-05-28T22:30:00Z", "type": "ASLEEP"},
                    {"startTime": "2026-05-28T22:30:00Z", "endTime": "2026-05-28T22:45:00Z", "type": "AWAKE"},
                    {"startTime": "2026-05-28T22:45:00Z", "endTime": "2026-05-28T23:00:00Z", "type": "RESTLESS"},
                ],
            },
        },
    )
    store.upsert_rollup(
        data_type="steps",
        rollup_point={
            "civilStartTime": {"date": {"year": 2026, "month": 5, "day": 28}, "time": {}},
            "civilEndTime": {"date": {"year": 2026, "month": 5, "day": 29}, "time": {}},
            "steps": {"count": 1234},
        },
    )

    summary = build_latest_summary(store, sleep_limit=1)

    assert summary["counts_by_data_type"]["sleep"] == 1
    assert summary["counts_by_data_type"]["steps:daily-rollup"] == 1
    assert summary["latest_sleep"][0]["display_sleep"] == "5h 45m"
    assert summary["latest_sleep"][0]["awake"] == "0h 15m"
    assert summary["latest_sleep"][0]["restless"] == "0h 15m"
    assert summary["latest_rollups"]["steps"]["start_time"] == "2026-05-28"
