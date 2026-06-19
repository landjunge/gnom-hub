from abc import ABC, abstractmethod
import json
from typing import Any
from .connection import get_db_conn

class StateRepository(ABC):
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any: pass
    @abstractmethod
    def set_value(self, key: str, value: Any) -> None: pass
    @abstractmethod
    def get_active_project(self) -> str: pass
    @abstractmethod
    def set_active_project(self, name: str) -> None: pass
    @abstractmethod
    def get_language(self) -> str: pass
    @abstractmethod
    def set_language(self, lang: str) -> None: pass

class SQLiteStateRepository(StateRepository):
    def get_value(self, key: str, default: Any = None) -> Any:
        with get_db_conn() as c:
            r = c.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return json.loads(r["value"]) if r else default
    def set_value(self, key: str, value: Any) -> None:
        with get_db_conn() as c, c:
            c.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    def get_active_project(self) -> str:
        return self.get_value("active_project", "default")
    def set_active_project(self, name: str) -> None:
        self.set_value("active_project", name.strip())
    def get_language(self) -> str:
        return self.get_value("language", "en")
    def set_language(self, lang: str) -> None:
        self.set_value("language", lang.strip().lower())
