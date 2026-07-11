"""Entity-Extraction: Text → Liste von (Entity, Properties).

Phase 1 des TKG-Plans: LLM-driven Entity-Extraktion.
Heuristik-First (deterministisch), LLM-Fallback wenn Heuristik leer.
"""
from __future__ import annotations

import re
from typing import Optional

from gnom_hub.memory_tkg.models import Entity


# ── Heuristik-Patterns (deterministisch, schnell) ──
# Format: (regex, type, importance)

_ENTITY_PATTERNS: list[tuple[re.Pattern, str, float]] = [
    # SCREAMING_SNAKE mit optionalem Bindestrich/Version (GPT-4, FAISS-v2, numpy<2)
    (re.compile(r"\b([A-Z][A-Z0-9]+(?:[-_][A-Z0-9]+){0,3})\b"), "code_id", 0.7),
    # Multi-Word PascalCase/CamelCase (KuzuDB, ChatGPT, OpenRouter)
    (re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b"), "code_id", 0.75),
    # Single PascalCase (Claude, Mistral, Llama) — min 5 chars
    (re.compile(r"\b([A-Z][a-z]{4,})\b"), "model", 0.65),
    # snake_case (sentence_transformers, pyproject_toml) — min 8 chars
    (re.compile(r"\b([a-z][a-z0-9_]{7,})\b"), "code_id", 0.5),
    # Dateien
    (re.compile(r"\b([\w\-/]+\.(?:py|js|ts|json|yaml|yml|md|sql|sh|bash|toml|html|css))\b"), "file", 0.5),
    # URLs / PRs
    (re.compile(r"\b(https?://[\w\-./]+)\b"), "url", 0.4),
    # Agents (per Konvention CamelCase mit AG-Suffix)
    (re.compile(r"\b(GeneralAG|SoulAG|CoderAG|WriterAG|ResearcherAG|EditorAG|WatchdogAG|SecurityAG)\b"), "agent", 0.9),
    # Fehler / Bugs
    (re.compile(r"\b([A-Z][A-Z0-9_\-]+_(?:BREAK|ERROR|FAIL|EXCEPTION|BUG))\b"), "bug", 0.85),
    (re.compile(r"\b(FAISS[_\-]?ABI[_\-]?BREAK|KuzuDB[_\-]?ERROR|numpy[_\-]?pin)\b", re.IGNORECASE), "bug", 0.85),
    # Datum
    (re.compile(r"\b(202[0-9]-\d{2}-\d{2})\b"), "date", 0.3),
]


# Stopwörter die KEINE Entities sind (zu generisch + Verben)
_STOPWORDS = {
    "UND", "ODER", "MIT", "AUS", "VON", "DER", "DIE", "DAS", "EIN", "EINE", "NICHT",
    "IST", "SIND", "WIRD", "WURDE", "HAT", "HABEN", "SEIN", "WERDEN", "KANN", "MUSS", "SOLL",
    "AUCH", "NUR", "NOCH", "MEHR", "WENIGER", "DIESE", "DIESER", "JEDER", "JEDE", "ALLE",
    "WIR", "IHR", "SIE", "ICH", "DU", "ER", "THE", "AND", "FOR", "WITH", "THIS", "THAT",
    "THE", "HAVE", "HAS", "HAD", "WILL", "WOULD", "COULD", "SHOULD", "BEEN", "BEING",
    "DEM", "DEN", "DES", "EINER", "EINES", "EINE", "EINEM", "EINEN", "ZU", "AUF", "UEBER",
    "UEBER", "DURCH", "OHNE", "MIT", "SEIT", "AUS", "BEI", "NACH", "VOR", "WIE", "WAS",
    # Verben / Adverbien / Funktionswörter
    "NUTZEN", "NUTZT", "JETZT", "STATT", "BESSER", "FIXTE", "GIBT", "MACHT", "MACHEN",
    "LAUFT", "LAEUFT", "SAGT", "GEHT", "KAM", "KOMMT", "STEHT", "SETZT", "LEGTE",
    "NEUEN", "NEUER", "ALTEN", "ALTER", "GANZ", "VIEL", "WENIG", "MANCHMAL", "OFT",
    "EINGESETZT", "ERSETZT", "GENUTZT", "BENUTZT", "VERWENDET", "GEMACHT", "GESAGT",
    "USE", "USES", "USED", "USING", "REPLACE", "REPLACED", "REPLACING", "MAKES", "MAKE",
}


def _slug(name: str) -> str:
    """Normalisiert Entity-Name zu slug-id (lowercase, underscores)."""
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower()
    return s or "unknown"


def extract_entities_heuristic(text: str) -> list[Entity]:
    """Deterministische Entity-Extraktion per Regex-Pattern."""
    if not text or len(text) < 5:
        return []

    found: dict[str, Entity] = {}  # dedup by name
    stopwords_lower = {s.lower() for s in _STOPWORDS}
    for pattern, etype, importance in _ENTITY_PATTERNS:
        for m in pattern.finditer(text):
            name = m.group(1)
            if len(name) < 4 or len(name) > 100:
                continue
            if name.upper() in _STOPWORDS or name.lower() in stopwords_lower:
                continue
            # Lowercase snake_case: skip if too common or just a verb form
            if etype == "code_id" and importance <= 0.5 and "_" in name:
                # snake_case nur behalten wenn >= 8 Zeichen (Compound-Begriffe)
                if len(name) < 8:
                    continue
            if name in found:
                # Bump importance wenn mehrfach gefunden
                found[name].importance = min(1.0, found[name].importance + 0.05)
                continue
            slug = _slug(name)
            found[name] = Entity(
                id=f"e_{slug}",
                name=name,
                type=etype,
                importance=importance,
                last_seen=0.0,
                properties={"source": "heuristic"},
            )

    return list(found.values())


def extract_entities(text: str, llm_call: Optional[callable] = None) -> list[Entity]:
    """Extrahiert Entities. Heuristik first, LLM-Fallback wenn < 3 Treffer.

    Args:
        text: Input-Text (User-Message, Agent-Output, etc.)
        llm_call: Optional callable(prompt: str) -> str. Wenn None und Heuristik leer,
                  werden nur die Heuristik-Treffer zurückgegeben.

    Returns:
        Liste von Entity-Objekten (dedupliziert, importance > 0.4)
    """
    entities = extract_entities_heuristic(text)

    # Wenn LLM verfügbar und Heuristik < 3 Treffer: nachladen
    if llm_call and len(entities) < 3:
        try:
            llm_entities = _extract_entities_llm(text, llm_call)
            existing = {e.name for e in entities}
            for e in llm_entities:
                if e.name not in existing:
                    entities.append(e)
        except Exception:
            # LLM fehlgeschlagen — heuristische Treffer reichen
            pass

    return [e for e in entities if e.importance >= 0.3]


_LLM_PROMPT = """Extrahiere die wichtigsten Entitäten (Personen, Konzepte, Tools, Dateien, Bugs) aus dem Text.
Gib NUR valides JSON zurück, keine Erklärungen. Format:
[
  {{"name": "<entity_name>", "type": "<person|concept|tool|file|bug|event>", "importance": <0.0-1.0>}}
]

TEXT:
{text}

JSON:"""


def _extract_entities_llm(text: str, llm_call: callable) -> list[Entity]:
    """LLM-basierte Entity-Extraktion (optional)."""
    import json
    prompt = _LLM_PROMPT.format(text=text[:2000])  # truncate für Token-Budget
    raw = llm_call(prompt).strip()

    # Versuche JSON zu extrahieren (manche LLMs antworten mit ```json Blöcken)
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()

    data = json.loads(raw)
    if not isinstance(data, list):
        return []

    entities = []
    for item in data[:20]:  # max 20
        if not isinstance(item, dict) or "name" not in item:
            continue
        name = str(item["name"]).strip()
        etype = str(item.get("type", "concept")).strip()
        importance = float(item.get("importance", 0.5))
        if not name:
            continue
        entities.append(Entity(
            id=f"e_{_slug(name)}",
            name=name,
            type=etype,
            importance=max(0.0, min(1.0, importance)),
            last_seen=0.0,
            properties={"source": "llm"},
        ))
    return entities
