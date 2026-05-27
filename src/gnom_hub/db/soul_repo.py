from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List
from .connection import get_db_conn

class SoulRepository(ABC):
    @abstractmethod
    def save_fact(self, key: str, value: str) -> None: pass
    @abstractmethod
    def get_relevant_facts(self, query: str) -> List[str]: pass

class SQLiteSoulRepository(SoulRepository):
    def save_fact(self, key: str, value: str) -> None:
        with get_db_conn() as c, c:
            c.execute("INSERT OR REPLACE INTO soul_memory (key, value, timestamp) VALUES (?, ?, ?)",
                      (key, value, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")))
    def get_relevant_facts(self, query: str) -> List[str]:
        with get_db_conn() as c:
            rows = c.execute("SELECT key, value FROM soul_memory ORDER BY timestamp DESC LIMIT 20").fetchall()
            return [f"{r['key']}: {r['value']}" for r in rows]
