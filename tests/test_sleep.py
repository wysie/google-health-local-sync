from google_health_local_sync.sleep import summarize_sleep_datapoint, seconds_to_hm


def test_summarize_classic_sleep_preserves_restless_awake_asleep():
    dp = {
        "name": "users/me/dataTypes/sleep/dataPoints/1",
        "dataSource": {"platform": "FITBIT", "recordingMethod": "AUTOMATIC"},
        "sleep": {
            "type": "CLASSIC",
            "interval": {"startTime": "2026-05-28T17:40:00Z", "endTime": "2026-05-28T23:48:00Z"},
            "sleepStages": [
                {"startTime": "2026-05-28T17:40:00Z", "endTime": "2026-05-28T18:16:00Z", "type": "AWAKE"},
                {"startTime": "2026-05-28T18:16:00Z", "endTime": "2026-05-28T18:26:00Z", "type": "RESTLESS"},
                {"startTime": "2026-05-28T18:26:00Z", "endTime": "2026-05-28T23:48:00Z", "type": "ASLEEP"},
            ],
        },
    }

    summary = summarize_sleep_datapoint(dp)

    assert summary["sleep_type"] == "CLASSIC"
    assert summary["platform"] == "FITBIT"
    assert summary["recording_method"] == "AUTOMATIC"
    assert summary["stage_seconds"] == {"AWAKE": 2160, "RESTLESS": 600, "ASLEEP": 19320}
    assert summary["time_in_bed_seconds"] == 22080
    assert summary["display_sleep_seconds"] == 19920
    assert summary["awake_seconds"] == 2160
    assert summary["restless_seconds"] == 600


def test_summarize_staged_sleep_uses_light_deep_rem():
    dp = {
        "sleep": {
            "type": "STAGES",
            "interval": {"startTime": "2026-05-28T17:40:00Z", "endTime": "2026-05-28T23:48:00Z"},
            "sleepStages": [
                {"startTime": "2026-05-28T17:40:00Z", "endTime": "2026-05-28T18:26:00Z", "type": "AWAKE"},
                {"startTime": "2026-05-28T18:26:00Z", "endTime": "2026-05-28T21:12:00Z", "type": "LIGHT"},
                {"startTime": "2026-05-28T21:12:00Z", "endTime": "2026-05-28T22:42:00Z", "type": "DEEP"},
                {"startTime": "2026-05-28T22:42:00Z", "endTime": "2026-05-28T23:47:00Z", "type": "REM"},
            ],
        }
    }

    summary = summarize_sleep_datapoint(dp)

    assert summary["stage_seconds"] == {"AWAKE": 2760, "LIGHT": 9960, "DEEP": 5400, "REM": 3900}
    assert summary["display_sleep_seconds"] == 19260
    assert summary["awake_seconds"] == 2760
    assert summary["restless_seconds"] == 0


def test_seconds_to_hm():
    assert seconds_to_hm(19920) == "5h 32m"
