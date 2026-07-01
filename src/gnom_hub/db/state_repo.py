import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from .connection import get_db_conn


class StateRepository(ABC):
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any: pass
    @abstractmethod
    def set_value(self, key: str, value: Any) -> None: pass
    @abstractmethod
    def merge_value(self, key: str, patch: Any) -> Any: ...
    @abstractmethod
    def get_active_project(self) -> str: pass
    @abstractmethod
    def set_active_project(self, name: str) -> None: pass
    @abstractmethod
    def get_language(self) -> str: pass
    @abstractmethod
    def set_language(self, lang: str) -> None: pass


# Whitelist von State-Keys die destruktiv überschrieben werden dürfen
# (z.B. komplette Snapshots, Run-Control). Alles andere MUSS gemerged werden,
# damit versehentliche Partial-Writes (z.B. ein einzelner Inline-Key) nicht
# den ganzen State platt machen.
_OVERWRITE_ALLOWED = {
    "active_project", "language", "active_preset", "active_showbox",
    "active_workflow", "ui_state", "dashboard_layout", "user_settings",
}
# Keys die IMMER gemerged werden müssen — partielle Updates statt Replace
_MERGE_REQUIRED = {
    "llm_keys", "llm_agents", "llm_preset_", "llm_models",
    "agent_settings", "agent_stats", "agent_sliders",
    "presets", "preset_", "workflow_tasks",
}


class SQLiteStateRepository(StateRepository):
    def get_value(self, key: str, default: Any = None) -> Any:
        with get_db_conn() as c:
            r = c.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return json.loads(r["value"]) if r else default
    def set_value(self, key: str, value: Any) -> None:
        with get_db_conn() as c, c:
            c.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    def merge_value(self, key: str, patch: Any) -> Any:
        """Atomar: lese bestehenden State, merge mit patch, schreibe zurück.

        Für dict-Patches: nested merge (ein Patch mit {"soulag": {...}} merged
        nur diesen Key, andere bleiben erhalten). Für list/primitive-Patches:
        Replace.

        Returns: das gemergte Result.
        """
        current = self.get_value(key, None)
        if current is None:
            merged = patch
        elif isinstance(current, dict) and isinstance(patch, dict):
            merged = {**current, **patch}
        else:
            merged = patch
        self.set_value(key, merged)
        return merged
    def get_active_project(self) -> str:
        return self.get_value("active_project", "default")
    def set_active_project(self, name: str) -> None:
        self.set_value("active_project", name.strip())
    def get_language(self) -> str:
        return self.get_value("language", "en")
    def set_language(self, lang: str) -> None:
        self.set_value("language", lang.strip().lower())


# Auto-Schutz: Wenn Aufrufer versuchen einen Merge-Required-Key komplett zu
# überschreiben, wird stattdessen gemerged. Verhindert die häufigsten Bugs
# bei denen ein Endpoint `{agent: cfg}` postet und damit alle anderen Agents
# aus `llm_agents` löscht.
_orig_set_value = SQLiteStateRepository.set_value
def _guarded_set_value(self, key: str, value: Any) -> None:
    needs_merge = key in _MERGE_REQUIRED or any(key.startswith(p) for p in _MERGE_REQUIRED)
    if needs_merge and isinstance(value, dict):
        current = self.get_value(key, None)
        if isinstance(current, dict) and current and value and not any(
            # Wenn Caller explizit mit _replace=True markiert hat, erlauben
            isinstance(v, dict) and v.get("_replace") for v in [value]
        ):
            # Partial-Write Schutz: nur dann überschreiben wenn value SUPERSET
            # aller existierenden Keys ist (Caller weiß was er tut). Sonst mergen.
            current_keys = set(current.keys())
            new_keys = set(value.keys())
            if not new_keys.issuperset(current_keys):
                # Partial write — stattdessen mergen und warnen
                logging.getLogger(__name__).warning(
                    "Guarded set_value('%s'): %d→%d keys, auto-merging to prevent data loss",
                    key, len(current_keys), len(new_keys)
                )
                value = {**current, **value}
    _orig_set_value(self, key, value)
SQLiteStateRepository.set_value = _guarded_set_value
