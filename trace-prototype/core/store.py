import json
import math
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

STORE_DB_PATH = Path("db/trace_store.db")


class PolicyEntry(BaseModel):
    policy_id: str
    patch_type: str        # "memory" | "instruction" | "tool_rule" | "workflow"
    content: str           # The actual rule text injected into the prompt
    scope: str = "global"  # "global" or "user:<user_id>"
    reason: str = ""
    commit_id: str
    parent_id: Optional[str] = None
    active: bool = True
    created_at: str


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _cosine_sim(text_a: str, text_b: str) -> float:
    vec_a = Counter(_tokenize(text_a))
    vec_b = Counter(_tokenize(text_b))
    common = set(vec_a.keys()) & set(vec_b.keys())
    dot = sum(vec_a[w] * vec_b[w] for w in common)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class PolicyStore:
    def __init__(self, db_path: Path = STORE_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS policies (
            policy_id TEXT PRIMARY KEY,
            patch_type TEXT NOT NULL,
            content TEXT NOT NULL,
            scope TEXT NOT NULL,
            reason TEXT,
            commit_id TEXT NOT NULL,
            parent_id TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS commits (
            commit_id TEXT PRIMARY KEY,
            parent_id TEXT,
            action TEXT NOT NULL,       -- 'commit' | 'rollback'
            diff_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        conn.commit()
        conn.close()

    def get_head_commit(self) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT commit_id FROM commits ORDER BY rowid DESC LIMIT 1;")
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def commit_patch(
        self,
        content: str,
        patch_type: str = "instruction",
        scope: str = "global",
        reason: str = "",
    ) -> PolicyEntry:
        parent_id = self.get_head_commit()
        commit_id = f"c_{uuid.uuid4().hex[:8]}"
        policy_id = f"p_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        entry = PolicyEntry(
            policy_id=policy_id,
            patch_type=patch_type,
            content=content,
            scope=scope,
            reason=reason,
            commit_id=commit_id,
            parent_id=parent_id,
            active=True,
            created_at=now,
        )

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO policies
            (policy_id, patch_type, content, scope, reason, commit_id, parent_id, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.policy_id,
                entry.patch_type,
                entry.content,
                entry.scope,
                entry.reason,
                entry.commit_id,
                entry.parent_id,
                1,
                entry.created_at,
            ),
        )
        cur.execute(
            "INSERT INTO commits (commit_id, parent_id, action, diff_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (commit_id, parent_id, "commit", entry.model_dump_json(), now),
        )
        conn.commit()
        conn.close()
        return entry

    def rollback_commit(self, commit_id: str) -> bool:
        """Deactivates all policies introduced in the specified commit."""
        now = datetime.now(timezone.utc).isoformat()
        parent_id = self.get_head_commit()
        rb_commit_id = f"rb_{uuid.uuid4().hex[:8]}"

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE policies SET active = 0 WHERE commit_id = ?;", (commit_id,))
        changed = cur.rowcount > 0
        if changed:
            cur.execute(
                "INSERT INTO commits (commit_id, parent_id, action, diff_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (rb_commit_id, parent_id, "rollback", json.dumps({"reverted_commit": commit_id}), now),
            )
        conn.commit()
        conn.close()
        return changed

    def get_active_policies(self, user_id: Optional[str] = None) -> List[PolicyEntry]:
        scopes = ["global"]
        if user_id:
            scopes.append(f"user:{user_id}")

        placeholders = ",".join("?" for _ in scopes)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT policy_id, patch_type, content, scope, reason, commit_id, parent_id, active, created_at
            FROM policies
            WHERE active = 1 AND scope IN ({placeholders})
            ORDER BY rowid ASC;
            """,
            scopes,
        )
        rows = cur.fetchall()
        conn.close()

        return [
            PolicyEntry(
                policy_id=r[0],
                patch_type=r[1],
                content=r[2],
                scope=r[3],
                reason=r[4],
                commit_id=r[5],
                parent_id=r[6],
                active=bool(r[7]),
                created_at=r[8],
            )
            for r in rows
        ]

    def retrieve_relevant(
        self, query: str, user_id: Optional[str] = None, top_k: int = 5
    ) -> List[str]:
        """Retrieves active policies ranked by similarity to the incoming query."""
        entries = self.get_active_policies(user_id=user_id)
        scored = sorted(
            entries,
            key=lambda e: _cosine_sim(query, e.content),
            reverse=True,
        )
        return [e.content for e in scored[:top_k]]

    def clear_all(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM policies;")
        cur.execute("DELETE FROM commits;")
        conn.commit()
        conn.close()