import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS exchanges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  user_text TEXT NOT NULL,
  bot_text TEXT NOT NULL,
  emotion TEXT,
  intensity REAL,
  is_crisis INTEGER NOT NULL DEFAULT 0,
  timestamp TEXT NOT NULL,
  formatted_timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_exchanges_user_ts ON exchanges(user_id, timestamp);

CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_user_key ON memories(user_id, key);
"""


@dataclass(frozen=True)
class ExchangeRow:
    user_text: str
    bot_text: str
    emotion: Optional[str]
    intensity: Optional[float]
    is_crisis: bool
    timestamp: str
    formatted_timestamp: str


class MemoryStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def _connect(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def add_exchange(
        self,
        *,
        user_id: str,
        user_text: str,
        bot_text: str,
        emotion: Optional[str],
        intensity: Optional[float],
        is_crisis: bool,
        timestamp: str,
        formatted_timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO exchanges(
                  user_id, user_text, bot_text, emotion, intensity, is_crisis,
                  timestamp, formatted_timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_text,
                    bot_text,
                    emotion,
                    intensity,
                    1 if is_crisis else 0,
                    timestamp,
                    formatted_timestamp,
                ),
            )

    def get_recent_exchanges(self, *, user_id: str, limit: int = 10) -> List[ExchangeRow]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT user_text, bot_text, emotion, intensity, is_crisis, timestamp, formatted_timestamp
                FROM exchanges
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, int(limit)),
            ).fetchall()

        # Return oldest->newest for context usage
        out: List[ExchangeRow] = []
        for r in reversed(rows):
            out.append(
                ExchangeRow(
                    user_text=r["user_text"],
                    bot_text=r["bot_text"],
                    emotion=r["emotion"],
                    intensity=r["intensity"],
                    is_crisis=bool(r["is_crisis"]),
                    timestamp=r["timestamp"],
                    formatted_timestamp=r["formatted_timestamp"],
                )
            )
        return out

    def delete_user_history(self, *, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM exchanges WHERE user_id = ?", (user_id,))

    def upsert_memory(self, *, user_id: str, key: str, value: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories(user_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET
                  value = excluded.value,
                  updated_at = excluded.updated_at
                """,
                (user_id, key, value, now),
            )

    def get_memories(self, *, user_id: str) -> Dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM memories WHERE user_id = ? ORDER BY key ASC",
                (user_id,),
            ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    def delete_user_memories(self, *, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))


_RE_SPACES = re.compile(r"\s+")


def extract_memories_from_text(text: str) -> Dict[str, str]:
    """
    Lightweight, rule-based “memory” extraction.
    Keeps it conservative to avoid storing sensitive info unintentionally.
    """
    t = _RE_SPACES.sub(" ", (text or "").strip())
    t_lower = t.lower()
    memories: Dict[str, str] = {}

    # Preferred name
    m = re.search(r"\bmy name is ([a-zA-Z][a-zA-Z \-']{0,40})\b", t_lower)
    if m:
        name = m.group(1).strip()
        # Stop at common continuation patterns ("and ...", "but ...", punctuation)
        for sep in (" and ", " but ", ",", ";", ".", "!", "?"):
            if sep in name:
                name = name.split(sep, 1)[0].strip()
        name = " ".join(part.capitalize() for part in name.split())
        # Keep names shortish (avoid capturing sentences)
        if 1 <= len(name) <= 40 and len(name.split()) <= 4:
            memories["preferred_name"] = name

    m = re.search(r"\bcall me ([a-zA-Z][a-zA-Z \-']{0,40})\b", t_lower)
    if m:
        name = m.group(1).strip()
        for sep in (" and ", " but ", ",", ";", ".", "!", "?"):
            if sep in name:
                name = name.split(sep, 1)[0].strip()
        name = " ".join(part.capitalize() for part in name.split())
        if 1 <= len(name) <= 40 and len(name.split()) <= 4:
            memories["preferred_name"] = name

    # Preference: "I like X"
    m = re.search(r"\bi (?:really )?(?:like|love|enjoy) ([^\.!\?]{1,80})", t_lower)
    if m:
        pref = m.group(1).strip()
        # Avoid capturing very broad personal data (addresses, phone numbers, etc.)
        if not re.search(r"\b\d{3,}\b", pref):
            memories["likes"] = pref

    return memories

