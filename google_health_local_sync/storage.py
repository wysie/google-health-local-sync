from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path.home() / ".hermes" / "google_health"


class GoogleHealthStore:
    def __init__(self, data_dir: str | Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir).expanduser()
        self.token_path = self.data_dir / "token.json"
        self.db_path = self.data_dir / "google_health.sqlite"

    def save_token(self, token: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps(token, indent=2, sort_keys=True))
        try:
            self.token_path.chmod(0o600)
        except OSError:
            pass

    def load_token(self) -> dict[str, Any]:
        return json.loads(self.token_path.read_text())

    def init_db(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS data_points (
                    data_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    update_time TEXT,
                    platform TEXT,
                    recording_method TEXT,
                    raw_json TEXT NOT NULL,
                    PRIMARY KEY (data_type, record_id)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert_datapoint(self, *, data_type: str, data_point: dict[str, Any]) -> bool:
        self.init_db()
        record_id = data_point.get("name") or json.dumps(data_point, sort_keys=True)
        data_source = data_point.get("dataSource") or {}
        payload = data_point.get(data_type.replace("-", "_")) or data_point.get(data_type) or {}
        interval = payload.get("interval") or {}
        start = interval.get("startTime") or payload.get("startTime")
        end = interval.get("endTime") or payload.get("endTime") or payload.get("sessionEndTime")
        update_time = payload.get("updateTime") or data_point.get("updateTime")
        raw_json = json.dumps(data_point, ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(
                """
                INSERT OR IGNORE INTO data_points
                  (data_type, record_id, start_time, end_time, update_time, platform, recording_method, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (data_type, record_id, start, end, update_time, data_source.get("platform"), data_source.get("recordingMethod"), raw_json),
            )
            if cur.rowcount == 0:
                con.execute(
                    """
                    UPDATE data_points
                    SET start_time=?, end_time=?, update_time=?, platform=?, recording_method=?, raw_json=?
                    WHERE data_type=? AND record_id=?
                    """,
                    (start, end, update_time, data_source.get("platform"), data_source.get("recordingMethod"), raw_json, data_type, record_id),
                )
                return False
            return True

    def list_datapoints(self, data_type: str, limit: int = 100) -> list[dict[str, Any]]:
        self.init_db()
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT * FROM data_points WHERE data_type=? ORDER BY COALESCE(end_time, update_time, record_id) DESC LIMIT ?",
                (data_type, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def counts_by_data_type(self) -> dict[str, int]:
        self.init_db()
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute("SELECT data_type, COUNT(*) FROM data_points GROUP BY data_type ORDER BY data_type").fetchall()
        return {str(k): int(v) for k, v in rows}

    def get_sync_state(self, key: str) -> dict[str, Any] | None:
        self.init_db()
        with sqlite3.connect(self.db_path) as con:
            row = con.execute("SELECT value_json FROM sync_state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_sync_state(self, key: str, value: dict[str, Any]) -> None:
        self.init_db()
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                INSERT INTO sync_state(key, value_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value, sort_keys=True)),
            )

    def clear_sync_state(self, key: str) -> None:
        self.init_db()
        with sqlite3.connect(self.db_path) as con:
            con.execute("DELETE FROM sync_state WHERE key=?", (key,))

    @staticmethod
    def _civil_date(civil_dt: dict[str, Any] | None) -> str | None:
        if not civil_dt:
            return None
        d = civil_dt.get("date") or {}
        if not all(k in d for k in ("year", "month", "day")):
            return None
        return f"{int(d['year']):04d}-{int(d['month']):02d}-{int(d['day']):02d}"

    def upsert_rollup(self, *, data_type: str, rollup_point: dict[str, Any]) -> bool:
        start = self._civil_date(rollup_point.get("civilStartTime"))
        end = self._civil_date(rollup_point.get("civilEndTime"))
        rollup_type = f"{data_type}:daily-rollup"
        record_id = f"users/me/dataTypes/{data_type}/dataPoints:dailyRollUp/{start or 'unknown'}_{end or 'unknown'}"
        wrapper = {"name": record_id, rollup_type: rollup_point}
        inserted = self.upsert_datapoint(data_type=rollup_type, data_point=wrapper)
        if start or end:
            with sqlite3.connect(self.db_path) as con:
                con.execute(
                    "UPDATE data_points SET start_time=?, end_time=? WHERE data_type=? AND record_id=?",
                    (start, end, rollup_type, record_id),
                )
        return inserted
