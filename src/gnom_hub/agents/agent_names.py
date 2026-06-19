# agent_names.py — Zentrale Agent-Name Normalisierung
# Einheitliches Mapping: alle Schreibweisen → kanonischer Name (generalAG, soulAG, ...)

_AGENT_NAME_MAP = {
    # System-Agents
    "generalag": "generalAG", "general_ag": "generalAG", "general-ag": "generalAG", "general": "generalAG",
    "soulag": "soulAG", "soul_ag": "soulAG", "soul-ag": "soulAG", "soul": "soulAG",
    "watchdogag": "watchdogAG", "watchdog_ag": "watchdogAG", "watchdog-ag": "watchdogAG", "watchdog": "watchdogAG",
    "securityag": "securityAG", "security_ag": "securityAG", "security-ag": "securityAG", "security": "securityAG",
    "system": "system",
    # Worker-Agents
    "coderag": "coderAG", "coder_ag": "coderAG", "coder-ag": "coderAG", "coder": "coderAG",
    "writerag": "writerAG", "writer_ag": "writerAG", "writer-ag": "writerAG", "writer": "writerAG",
    "editorag": "editorAG", "editor_ag": "editorAG", "editor-ag": "editorAG", "editor": "editorAG",
    "researcherag": "researcherAG", "researcher_ag": "researcherAG", "researcher-ag": "researcherAG", "researcher": "researcherAG",
    # Standard-Layer
    "user": "user", "worker": "worker",
}


def normalize_agent_name(name: str) -> str:
    """Mappe alle Agent-Namensvarianten auf kanonischen Namen (generalAG, soulAG, ...).
    Unbekannte Namen werden unverändert zurückgegeben."""
    if not name:
        return name
    return _AGENT_NAME_MAP.get(name.lower(), name)


def normalize_showbox_name(name: str) -> str:
    """Normalisiert Showbox-Presentation-Namen, z.B. 'general_ag_pro_final' → 'generalAG'."""
    if not name:
        return name
    lower = name.lower()
    # Direkter Match
    if lower in _AGENT_NAME_MAP:
        return _AGENT_NAME_MAP[lower]
    # Bekannter Prefix-Match: 'general_ag_pro_final' → 'generalAG'
    for key in ("generalag", "soulag", "coderag", "writerag", "editorag", "researcherag", "watchdogag", "securityag"):
        if lower.startswith(key) or key in lower:
            return _AGENT_NAME_MAP[key]
    return name
