import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional
from pydantic import BaseModel

STORE_DB_PATH = Path("db/trace_store.db")

SignalType = Literal[
    "thumbs_up",
    "thumbs_down",
    "rating",
    "correction",
    "accept",
    "reject",
    "regenerate",
    "edit_distance",
    "abandon",
]


class FeedbackEvent(BaseModel):
    event_id: str
    task_id: str
    user_id: str
    question: str
    trace_json: str
    output: str
    signal_type: SignalType
    value: Any
    timestamp: str


class FeedbackCollector:
    def __init__(self, db_path: Path = STORE_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback_events (
            event_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            question TEXT NOT NULL,
            trace_json TEXT NOT NULL,
            output TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            value TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """)
        conn.commit()
        conn.close()

    def record(
        self,
        task_id: str,
        user_id: str,
        question: str,
        trace_json: str,
        output: str,
        signal_type: SignalType,
        value: Any,
    ) -> FeedbackEvent:
        event = FeedbackEvent(
            event_id=f"ev_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            user_id=user_id,
            question=question,
            trace_json=trace_json,
            output=output,
            signal_type=signal_type,
            value=str(value),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO feedback_events
            (event_id, task_id, user_id, question, trace_json, output, signal_type, value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.task_id,
                event.user_id,
                event.question,
                event.trace_json,
                event.output,
                event.signal_type,
                event.value,
                event.timestamp,
            ),
        )
        conn.commit()
        conn.close()
        return event

    def get_user_history(self, user_id: str, limit: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT event_id, task_id, signal_type, value, timestamp
            FROM feedback_events
            WHERE user_id = ?
            ORDER BY rowid DESC LIMIT ?;
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "event_id": r[0],
                "task_id": r[1],
                "signal_type": r[2],
                "value": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]