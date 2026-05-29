from __future__ import annotations

from datetime import datetime


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds_between(start: str, end: str) -> int:
    return int((parse_time(end) - parse_time(start)).total_seconds())


def seconds_to_hm(seconds: int | float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


def _sleep_payload(dp: dict) -> dict:
    if "sleep" in dp:
        return dp["sleep"] or {}
    return dp


def _interval(sleep: dict) -> tuple[str | None, str | None]:
    interval = sleep.get("interval") or {}
    start = interval.get("startTime") or sleep.get("startTime") or sleep.get("start")
    end = interval.get("endTime") or sleep.get("endTime") or sleep.get("sessionEndTime") or sleep.get("session_end_time")
    return start, end


def _stages(sleep: dict) -> list[dict]:
    return sleep.get("sleepStages") or sleep.get("stages") or sleep.get("levels") or []


def _stage_type(stage: dict) -> str:
    return str(stage.get("type") or stage.get("stage") or stage.get("level") or "UNKNOWN").upper()


def _stage_seconds(stage: dict) -> int:
    if "duration_seconds" in stage:
        return int(round(float(stage["duration_seconds"])))
    if "duration" in stage:
        value = stage["duration"]
        if isinstance(value, (int, float)):
            return int(round(float(value)))
        if isinstance(value, str) and value.endswith("s"):
            return int(round(float(value[:-1])))
    start = stage.get("startTime") or stage.get("start_time") or stage.get("start")
    end = stage.get("endTime") or stage.get("end_time") or stage.get("end")
    if start and end:
        return seconds_between(start, end)
    return 0


def summarize_sleep_datapoint(dp: dict) -> dict:
    sleep = _sleep_payload(dp)
    data_source = dp.get("dataSource") or {}
    start, end = _interval(sleep)
    stage_seconds: dict[str, int] = {}
    for stage in _stages(sleep):
        kind = _stage_type(stage)
        stage_seconds[kind] = stage_seconds.get(kind, 0) + _stage_seconds(stage)

    if start and end:
        time_in_bed = seconds_between(start, end)
    else:
        time_in_bed = sum(stage_seconds.values())

    awake_seconds = stage_seconds.get("AWAKE", 0) + stage_seconds.get("1", 0)
    restless_seconds = stage_seconds.get("RESTLESS", 0)

    sleep_stage_names = {"ASLEEP", "LIGHT", "DEEP", "REM", "SLEEPING", "2", "4", "5", "6"}
    display_sleep_seconds = restless_seconds + sum(v for k, v in stage_seconds.items() if k in sleep_stage_names)

    # If there are no recognized sleep stages, fall back to time-in-bed minus awake.
    if display_sleep_seconds == 0 and time_in_bed:
        display_sleep_seconds = max(0, time_in_bed - awake_seconds)

    return {
        "name": dp.get("name"),
        "platform": data_source.get("platform"),
        "recording_method": data_source.get("recordingMethod"),
        "data_source": data_source,
        "sleep_type": sleep.get("type") or sleep.get("sleepType"),
        "start": start,
        "end": end,
        "time_in_bed_seconds": time_in_bed,
        "stage_seconds": stage_seconds,
        "display_sleep_seconds": display_sleep_seconds,
        "awake_seconds": awake_seconds,
        "restless_seconds": restless_seconds,
    }
