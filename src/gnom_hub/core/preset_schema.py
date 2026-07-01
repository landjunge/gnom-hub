"""Preset-Schema für Gnom-Hub.

Definiert 14 Pydantic-Modelle, die zusammen ein vollständiges Preset-Bundle
beschreiben. Pro Preset-ID existiert ein Ordner unter ``data/presets/<id>/``
mit 14 gleichnamigen JSON-Dateien.

Die Schema-Datei ist absichtlich frei von Seiteneffekten — sie darf in
Tests und vom Loader ohne weitere Initialisierung importiert werden.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


class AgentDef(BaseModel):
    """Definition eines einzelnen Agents (System-Agent oder Worker).

    Felder:
        name:            Anzeigename.
        role:            Logische Rolle (soul, watchdog, general, security,
                         writer, coder, researcher, editor).
        prompt:          Vollständiger System-Prompt.
        model_override:  Optional — wenn gesetzt, wird dieses Modell statt
                         der rollen-basierten Default-Auswahl verwendet.
                         ``None`` heißt: Router entscheidet anhand Rolle.
        model_locked:    Wenn True, darf die UI das Modell nicht überschreiben.
                         SoulAG setzt dies auf True.
        priority:        Routing-Priorität (``lowest``, ``low``, ``normal``,
                         ``high``, ``highest``). SoulAG = ``highest``.
        enabled:         Agent ist aktiv und kann angesprochen werden.
        description:     Kurzbeschreibung für UI-Listen.
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=80)
    role: str = Field(..., min_length=1, max_length=40)
    prompt: str = Field(..., min_length=1)
    model_override: str | None = None
    model_locked: bool = False
    priority: str = Field(default="normal")
    enabled: bool = True
    description: str = Field(default="")

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, v: str) -> str:
        allowed = {"lowest", "low", "normal", "high", "highest"}
        if v not in allowed:
            raise ValueError(f"priority must be one of {sorted(allowed)}, got {v!r}")
        return v


class ToolDef(BaseModel):
    """Definition eines Werkzeugs, das Agents/Workern zur Verfügung steht."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=60)
    name: str = Field(..., min_length=1, max_length=80)
    capability: str = Field(..., min_length=1, max_length=60)
    description: str = Field(default="")
    allowed_agents: list[str] = Field(default_factory=list)
    allowed_workers: list[str] = Field(default_factory=list)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class PluginDef(BaseModel):
    """Definition eines optionalen Plugins."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=60)
    name: str = Field(..., min_length=1, max_length=80)
    version: str = Field(default="0.1.0")
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="")


class TemplateDef(BaseModel):
    """Definition eines Prompt-Templates."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=60)
    name: str = Field(..., min_length=1, max_length=80)
    body: str = Field(..., min_length=1)
    variables: list[str] = Field(default_factory=list)
    description: str = Field(default="")


class WorkflowStep(BaseModel):
    """Ein einzelner Schritt innerhalb eines Workflows."""

    model_config = ConfigDict(extra="allow")

    agent_id: str = Field(..., min_length=1, max_length=80)
    role: str = Field(default="normal")
    depends_on: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="")


class WorkflowDef(BaseModel):
    """Definition eines Workflow-Szenarios."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=60)
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="")
    steps: list[WorkflowStep] = Field(default_factory=list)
    enabled: bool = True


class WebhookDef(BaseModel):
    """Definition eines eingehenden Webhooks."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=60)
    url: str = Field(..., min_length=1)
    secret_ref: str = Field(..., min_length=1)
    enabled: bool = True
    event_filter: list[str] = Field(default_factory=list)
    description: str = Field(default="")


class HookDef(BaseModel):
    """Definition eines internen Hooks."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=60)
    event: str = Field(..., min_length=1, max_length=60)
    agent_id: str = Field(..., min_length=1, max_length=80)
    action: str = Field(..., min_length=1)
    enabled: bool = True
    priority: int = Field(default=100, ge=0, le=1000)


class SkillDef(BaseModel):
    """Definition eines gelernten Skills / Verhaltens."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=60)
    name: str = Field(..., min_length=1, max_length=80)
    body: str = Field(..., min_length=1)
    learned_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


class MCPInterface(BaseModel):
    """Definition eines externen MCP-Interfaces."""

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    id: str = Field(..., min_length=1, max_length=60)
    name: str = Field(..., min_length=1, max_length=80)
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        alias="schema",
        description="JSON-Schema für eingehende MCP-Requests.",
    )
    allowed_clients: list[str] = Field(default_factory=list)
    description: str = Field(default="")
    enabled: bool = True


# ---------------------------------------------------------------------------
# Top-level modelle pro JSON-Datei
# ---------------------------------------------------------------------------


class PresetConfig(BaseModel):
    """``config.json`` — allgemeine Preset-Metadaten und Schieberegler."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1, max_length=20)
    personality: int = Field(..., ge=1, le=5)
    response_style: int = Field(..., ge=1, le=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: list[str] = Field(default_factory=list)


class SystemAgentsConfig(BaseModel):
    """``system_agents.json`` — die vier System-Agents."""

    model_config = ConfigDict(extra="allow")

    soul: AgentDef
    watchdog: AgentDef
    general: AgentDef
    security: AgentDef


class WorkersConfig(BaseModel):
    """``workers.json`` — die vier Standard-Worker."""

    model_config = ConfigDict(extra="allow")

    writer: AgentDef
    coder: AgentDef
    researcher: AgentDef
    editor: AgentDef


class ToolsConfig(BaseModel):
    """``tools.json`` — alle verfügbaren Werkzeuge."""

    model_config = ConfigDict(extra="allow")

    tools: list[ToolDef] = Field(default_factory=list)


class PluginsConfig(BaseModel):
    """``plugins.json`` — aktivierte Plugins."""

    model_config = ConfigDict(extra="allow")

    plugins: list[PluginDef] = Field(default_factory=list)


class TemplatesConfig(BaseModel):
    """``templates.json`` — Prompt-Templates."""

    model_config = ConfigDict(extra="allow")

    templates: list[TemplateDef] = Field(default_factory=list)


class WorkflowsConfig(BaseModel):
    """``workflows.json`` — Workflow-Szenarien."""

    model_config = ConfigDict(extra="allow")

    workflows: list[WorkflowDef] = Field(default_factory=list)


class MemoryConfig(BaseModel):
    """``memory.json`` — Memory/Soul-Memory-Einstellungen."""

    model_config = ConfigDict(extra="allow")

    soul_memory_enabled: bool = True
    vector_store: str = Field(default="faiss")
    max_entries: int = Field(default=10000, ge=0)
    retention_days: int = Field(default=90, ge=0)
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    extra: dict[str, Any] = Field(default_factory=dict)


class SecurityConfig(BaseModel):
    """``security.json`` — Sicherheits- und Schlüssel-Einstellungen."""

    model_config = ConfigDict(extra="allow")

    encryption_at_rest: bool = True
    require_usb_key: bool = False
    usb_key_id: str | None = None
    allowed_api_origins: list[str] = Field(default_factory=list)
    key_rotation_days: int = Field(default=30, ge=0)
    secret_slots: list[str] = Field(default_factory=list)


class WebhooksConfig(BaseModel):
    """``webhooks.json`` — eingehende Webhooks."""

    model_config = ConfigDict(extra="allow")

    incoming: list[WebhookDef] = Field(default_factory=list)


class HooksConfig(BaseModel):
    """``hooks.json`` — interne Event-Hooks."""

    model_config = ConfigDict(extra="allow")

    internal: list[HookDef] = Field(default_factory=list)


class SkillsConfig(BaseModel):
    """``skills.json`` — gelernte Skills."""

    model_config = ConfigDict(extra="allow")

    skills: list[SkillDef] = Field(default_factory=list)


class PermissionsConfig(BaseModel):
    """``permissions.json`` — Berechtigungs-Matrix Agent → Capabilities.

    Status: **DORMANT** (Validierungs-only, Stand 2026-06-21).
    Das Schema existiert, die Datei wird via ``preset_loader.py:53,195,302``
    registriert/validiert/geschrieben — aber **kein** Runtime-Pfad liest
    ``permissions.matrix`` für tatsächliche Permission-Entscheidungen.
    Runtime-Permissions kommen ausschließlich aus
    ``agents/agent_definitions.py`` (siehe ``agent_definitions.py:32-40``
    und ``inventory.md:529-624``). Token-Vokabular ist inkompatibel
    (A: ``read,write,run,godmode,desktop,crawl,evolve,web_search,browser,@job``
    vs. B: ``read,write,exec,network,memory,admin``). Konsolidierung mit
    Vocabulary A ist ein separater Refactor-Schritt — siehe
    ``docs/refactor-permissions/dependent-changes.md`` Schritt 3.
    """

    model_config = ConfigDict(extra="allow")

    matrix: dict[str, list[str]] = Field(default_factory=dict)
    description: str = Field(default="")


class MCPConfig(BaseModel):
    """``mcp.json`` — externe MCP-Schnittstellen."""

    model_config = ConfigDict(extra="allow")

    exposed: list[MCPInterface] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Bundle — fasst alle 14 Sub-Modelle zu einem in-memory Objekt zusammen
# ---------------------------------------------------------------------------


# Canonical filenames — Reihenfolge ist gleichzeitig die Schreib-Reihenfolge
PRESET_FILES: tuple[str, ...] = (
    "config.json",
    "system_agents.json",
    "workers.json",
    "tools.json",
    "plugins.json",
    "templates.json",
    "workflows.json",
    "memory.json",
    "security.json",
    "webhooks.json",
    "hooks.json",
    "skills.json",
    "permissions.json",
    "mcp.json",
)


class PresetBundle(BaseModel):
    """In-Memory-Repräsentation eines kompletten Presets.

    Jedes Attribut entspricht einer JSON-Datei in ``data/presets/<id>/``.
    """

    model_config = ConfigDict(extra="forbid")

    config: PresetConfig
    system_agents: SystemAgentsConfig
    workers: WorkersConfig
    tools: ToolsConfig
    plugins: PluginsConfig
    templates: TemplatesConfig
    workflows: WorkflowsConfig
    memory: MemoryConfig
    security: SecurityConfig
    webhooks: WebhooksConfig
    hooks: HooksConfig
    skills: SkillsConfig
    permissions: PermissionsConfig
    mcp: MCPConfig

    # Convenience Aggregationen -------------------------------------------------

    @property
    def all_agent_ids(self) -> list[str]:
        """Union aller Agent-Namen aus system_agents + workers.

        Wird vom Loader für Cross-File-Validierung genutzt.
        """
        ids: list[str] = []
        for sa in (
            self.system_agents.soul,
            self.system_agents.watchdog,
            self.system_agents.general,
            self.system_agents.security,
        ):
            ids.append(sa.name)
        for w in (
            self.workers.writer,
            self.workers.coder,
            self.workers.researcher,
            self.workers.editor,
        ):
            ids.append(w.name)
        return ids


class PresetSummary(BaseModel):
    """Kurzform für ``list_presets``."""

    id: str
    name: str
    description: str
    version: str
    updated_at: datetime


__all__ = [
    "AgentDef",
    "ToolDef",
    "PluginDef",
    "TemplateDef",
    "WorkflowStep",
    "WorkflowDef",
    "WebhookDef",
    "HookDef",
    "SkillDef",
    "MCPInterface",
    "PresetConfig",
    "SystemAgentsConfig",
    "WorkersConfig",
    "ToolsConfig",
    "PluginsConfig",
    "TemplatesConfig",
    "WorkflowsConfig",
    "MemoryConfig",
    "SecurityConfig",
    "WebhooksConfig",
    "HooksConfig",
    "SkillsConfig",
    "PermissionsConfig",
    "MCPConfig",
    "PresetBundle",
    "PresetSummary",
    "PRESET_FILES",
]