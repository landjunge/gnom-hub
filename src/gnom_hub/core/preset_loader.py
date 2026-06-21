"""Preset-Bundle-Loader/Saver.

Liest und schreibt Preset-Ordner unter ``data/presets/<preset_id>/``.
Jeder Ordner enthält 14 JSON-Dateien (siehe ``PRESET_FILES``).

Schreibvorgänge sind atomar: erst in ``*.tmp`` schreiben, dann ``os.replace``.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .preset_schema import (
    PRESET_FILES,
    HooksConfig,
    MCPConfig,
    MemoryConfig,
    PermissionsConfig,
    PluginsConfig,
    PresetBundle,
    PresetConfig,
    PresetSummary,
    SecurityConfig,
    SkillsConfig,
    SystemAgentsConfig,
    TemplatesConfig,
    ToolsConfig,
    WebhooksConfig,
    WorkflowsConfig,
    WorkersConfig,
)


# Dateiname (ohne .json) → Pydantic-Klasse
_FILE_TO_MODEL: dict[str, type] = {
    "config": PresetConfig,
    "system_agents": SystemAgentsConfig,
    "workers": WorkersConfig,
    "tools": ToolsConfig,
    "plugins": PluginsConfig,
    "templates": TemplatesConfig,
    "workflows": WorkflowsConfig,
    "memory": MemoryConfig,
    "security": SecurityConfig,
    "webhooks": WebhooksConfig,
    "hooks": HooksConfig,
    "skills": SkillsConfig,
    "permissions": PermissionsConfig,
    "mcp": MCPConfig,
}


def _preset_root() -> Path:
    """Projekt-Root für Presets: ``<repo>/data/presets``.

    Wir verlassen uns auf den klassischen Pfad ``data/presets/`` direkt im
    Repo, damit Tests deterministisch laufen.
    """
    # src/gnom_hub/core/preset_loader.py → repo_root ist parents[3]
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    return repo_root / "data" / "presets"


def get_presets_root() -> Path:
    """Öffentlicher Alias für ``_preset_root()`` — legt das Verzeichnis an.

    Wird vom API-Layer (FastAPI-Endpoints) und von Tests verwendet, um
    programmatisch an den Preset-Root-Pfad zu kommen.
    """
    root = _preset_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def preset_dir(preset_id: str) -> Path:
    """Liefert den Pfad ``data/presets/<preset_id>``.

    Lehnt unsichere IDs ab (leer, mit Pfad-Trennzeichen oder ``..``), um
    Path-Traversal außerhalb des Preset-Roots zu verhindern.
    """
    if not isinstance(preset_id, str) or not preset_id.strip():
        raise ValueError(f"Ungültige preset_id: {preset_id!r}")
    if "/" in preset_id or "\\" in preset_id or ".." in preset_id:
        raise ValueError(f"Ungültige preset_id (Path-Traversal): {preset_id!r}")
    return _preset_root() / preset_id


def ensure_default_preset_exists() -> Path:
    """Stellt sicher, dass der Default-Preset-Ordner existiert.

    Legt das Verzeichnis ``data/presets/default`` an, falls nicht vorhanden.
    Die Default-JSONs werden über die Versionsverwaltung (Git) geliefert.
    """
    pdir = preset_dir("default")
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir


def now_utc():
    """Aktuelle UTC-Zeit mit ``tzinfo=UTC`` (für ``updated_at``-Felder)."""
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Atomar schreiben: erst ``*.tmp`` schreiben, dann ``os.replace``.

    ``os.replace`` ist auf POSIX atomar, daher sieht ein Reader nie eine
    halb geschriebene Datei.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        finally:
            raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_preset(preset_id: str) -> PresetBundle:
    """Lade alle 14 JSON-Dateien und validiere sie als ``PresetBundle``.

    Raises:
        FileNotFoundError: Preset-Ordner oder eine der 14 Dateien fehlt.
        ValueError: Mindestens eine Datei ist kein valides JSON oder
            verstößt gegen das Schema.
    """
    root = preset_dir(preset_id)
    if not root.is_dir():
        raise FileNotFoundError(f"Preset '{preset_id}' not found at {root}")

    payload: dict[str, Any] = {}
    for filename in PRESET_FILES:
        key = filename[: -len(".json")]
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Preset '{preset_id}' is missing file '{filename}' at {path}"
            )
        raw = _read_json(path)
        model_cls = _FILE_TO_MODEL[key]
        # Pydantic v2: model_validate für Dict → Modell
        payload[key] = model_cls.model_validate(raw)

    return PresetBundle(**payload)


def save_preset(preset_id: str, bundle: PresetBundle) -> None:
    """Schreibe alle 14 Sub-Modelle als JSON-Dateien in den Preset-Ordner.

    Atomar pro Datei (tmp + replace) — bei einem Fehler bleiben alle
    bereits geschriebenen Dateien unverändert.
    """
    root = preset_dir(preset_id)
    root.mkdir(parents=True, exist_ok=True)

    mapping: dict[str, Any] = {
        "config": bundle.config,
        "system_agents": bundle.system_agents,
        "workers": bundle.workers,
        "tools": bundle.tools,
        "plugins": bundle.plugins,
        "templates": bundle.templates,
        "workflows": bundle.workflows,
        "memory": bundle.memory,
        "security": bundle.security,
        "webhooks": bundle.webhooks,
        "hooks": bundle.hooks,
        "skills": bundle.skills,
        "permissions": bundle.permissions,
        "mcp": bundle.mcp,
    }

    for filename in PRESET_FILES:
        key = filename[: -len(".json")]
        model = mapping[key]
        # by_alias=True sorgt dafür, dass Aliase (z. B. ``schema`` für MCPInterface)
        # beim Serialisieren mit dem im JSON verwendeten Namen erscheinen.
        data = model.model_dump(mode="json", by_alias=True)
        _write_json_atomic(root / filename, data)


def list_presets() -> list[PresetSummary]:
    """Liste alle Preset-IDs, die einen vollständigen Bundle-Ordner haben.

    Presets, denen mindestens eine der 14 Dateien fehlt, werden übersprungen.
    """
    root = _preset_root()
    if not root.is_dir():
        return []
    out: list[PresetSummary] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        try:
            bundle = load_preset(entry.name)
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            # Unvollständiges oder invalides Preset überspringen
            continue
        out.append(
            PresetSummary(
                id=entry.name,
                name=bundle.config.name,
                description=bundle.config.description,
                version=bundle.config.version,
                updated_at=bundle.config.updated_at,
            )
        )
    return out


def delete_preset(preset_id: str) -> bool:
    """Lösche den Preset-Ordner.

    Returns:
        True bei Erfolg, False wenn der Ordner nicht existiert.

    Raises:
        PermissionError: Versuch, das ``default``-Preset zu löschen.
    """
    if preset_id == "default":
        raise PermissionError(
            "Das 'default'-Preset ist geschützt und darf nicht gelöscht werden."
        )
    root = preset_dir(preset_id)
    if not root.is_dir():
        return False
    shutil.rmtree(root)
    return True


# ---------------------------------------------------------------------------
# Cross-File-Validierung
# ---------------------------------------------------------------------------


def validate_preset_bundle(bundle: PresetBundle) -> list[str]:
    """Semantische Cross-File-Validierung.

    Prüft:
      * Alle in ``tools.json`` referenzierten Agent-IDs müssen in
        ``system_agents.json`` oder ``workers.json`` existieren.
      * Alle ``workflows.json``-Steps zeigen auf existente Agents.
      * ``permissions.json``-Keys müssen Union aus system+workers sein.
      * ``webhooks.json`` secret_refs müssen in ``security.json.secret_slots``
        definiert sein.

    Returns:
        Liste mit Fehlermeldungen. Leere Liste = alles ok.
    """
    errors: list[str] = []

    agent_names = set(bundle.all_agent_ids)

    # 1) Tool references
    for tool in bundle.tools.tools:
        for agent_id in tool.allowed_agents:
            if agent_id not in agent_names:
                errors.append(
                    f"tool '{tool.id}' verweist auf unbekannten agent '{agent_id}'"
                )
        for worker_id in tool.allowed_workers:
            if worker_id not in agent_names:
                errors.append(
                    f"tool '{tool.id}' verweist auf unbekannten worker '{worker_id}'"
                )

    # 2) Workflow steps
    for wf in bundle.workflows.workflows:
        for step in wf.steps:
            if step.agent_id not in agent_names:
                errors.append(
                    f"workflow '{wf.id}' step '{step.agent_id}' verweist auf unbekannten agent"
                )

    # 3) Permissions matrix keys
    # NOTE: DORMANT — siehe permissions.json:_status + agent_definitions.py:32-40
    # Validierung der Key-Set-Zugehörigkeit ist die einzige Runtime-Nutzung von
    # permissions.matrix; Capability-Tokens werden nirgends konsumiert.
    for agent_id in bundle.permissions.matrix.keys():
        if agent_id not in agent_names:
            errors.append(
                f"permissions.matrix hat unbekannten agent '{agent_id}'"
            )

    # 4) Webhook secret_refs
    allowed_slots = set(bundle.security.secret_slots or [])
    for wh in bundle.webhooks.incoming:
        if wh.secret_ref not in allowed_slots:
            errors.append(
                f"webhook '{wh.id}' secret_ref '{wh.secret_ref}' nicht in security.secret_slots"
            )

    return errors


__all__ = [
    "load_preset",
    "save_preset",
    "list_presets",
    "delete_preset",
    "validate_preset_bundle",
    "preset_dir",
    "get_presets_root",
    "ensure_default_preset_exists",
    "now_utc",
]