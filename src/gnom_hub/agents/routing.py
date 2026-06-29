"""routing.py — Deterministic Capability-Routing for gnom-hub.

Sitzt zwischen dem LLM-Routing-Intent (z.B. ``GeneralAG`` will ``CoderAG``
delegieren) und dem bestehenden :func:`gnom_hub.agents.swarm.swarm_comms.dispatch_by_capability`.
Ziel: **keine LLM-Halluzination** bei der Frage "welcher Agent bekommt
den Sub-Task?".

Design-Prinzipien
─────────────────

1. **Deterministisch.** Keine LLM-Calls innerhalb dieses Moduls. Die
   Auflösung basiert auf einer kleinen, von Hand kuratierten Synonymtabelle
   (``_CANONICAL_CAPABILITIES``) plus einer Phrase-Tabelle für
   Mehrwort-Intents (EN + DE) — vorhersagbare Tokenisierung.
2. **Rein.** Keine neuen externen Abhängigkeiten. Nur ``re`` und der
   Stdlib-Tokenizer.
3. **Fallback-freundlich.** Wenn nichts matcht, liefert die API
   ``("", 0.0, "none")``. Die aufrufende Schicht (siehe
   :func:`build_fallback_chain`) entscheidet dann, was passiert (z.B.
   ``"general"`` als Catch-All).
4. **Brücke zum Offload-System.** :func:`resolve_with_node_id` akzeptiert
   einen Callable für die ``node_id``-Auflösung; default greift auf
   :func:`gnom_hub.memory.node_resolver.resolve_node` zurück. So kann der
   Resolver Offload-Content als High-Confidence-Override-Source nutzen.

Öffentliche API
───────────────

- :func:`resolve_capability` — keywordbasiert, ohne Side-Effects.
- :func:`resolve_with_node_id` — wie oben, mit Offload-Bridge.
- :func:`build_fallback_chain` — vorhersagbare Reihenfolge bei
  Dead-End-Routing.

Alles andere ist Modul-Intern (``_CANONICAL_CAPABILITIES``,
``_PHRASE_PATTERNS``, ``_tokenize``).
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Callable, Literal, Optional

logger = logging.getLogger(__name__)


# ── Public Types ────────────────────────────────────────────────────────────

SourceTag = Literal["exact_match", "synonym", "fallback", "node_id_override", "none"]


@dataclass(frozen=True)
class ResolvedCapability:
    """Result of a capability resolution.

    Attributes
    ----------
    capability
        Canonical capability name (z.B. ``"shell"``). Empty string when
        nothing matched (``source == "none"``).
    confidence
        Score im Intervall [0.0, 1.0]:
        1.0 für Exact-Match (oder Phrase-Exact), 0.7 für Synonym-Match,
        0.3 für Fallback (gefilterter Match → ``"general"`` Catch-All),
        >=0.95 für Node-ID-Override.
    source
        Welcher Pfad hat geliefert. ``"none"`` heißt: nichts gefunden,
        Caller darf frei entscheiden.
    """

    capability: str
    confidence: float
    source: SourceTag


# ── Phrase-Tabelle ──────────────────────────────────────────────────────────
#
# Phrasen werden mit Wortgrenzen gematcht (längste zuerst). Sie überschreiben
# die Single-Token-Resolution, weil Mehrwort-Intents spezifischer sind
# (z.B. "write a file" → write_file statt der allgemeinen "write").


_PHRASE_PATTERNS: dict[str, str] = {
    # File-I/O
    "write a file": "write_file",
    "write the file": "write_file",
    "write this file": "write_file",
    "write file": "write_file",
    "schreibe datei": "write_file",
    "schreib datei": "write_file",
    "schreibe die datei": "write_file",
    "schreibe diese datei": "write_file",
    "read file": "file_read",
    "lies datei": "file_read",
    "read the file": "file_read",
    "lies die datei": "file_read",
    # Texte / Content
    "write an article": "content_creation",
    "write a document": "content_creation",
    "write documentation": "content_creation",
    "schreibe artikel": "content_creation",
    "schreibe dokumentation": "content_creation",
    # Web-Recherche
    "web search": "search_web",
    "web research": "web_research",
    "do research": "web_research",
    "fact check": "fact_checking",
    "faktencheck": "fact_checking",
    # Coordination (mehrwortige Trigger-Phrasen)
    "dispatch task": "coordination",
    "dispatch the task": "coordination",
    "verteile aufgabe": "coordination",
    "delegiere aufgabe": "coordination",
    # Profile-Management
    "manage my profile": "profile_management",
    "user settings": "profile_management",
    "user-einstellungen": "profile_management",
    # Summarization (DE)
    "fasse zusammen": "summarization",
    "fass zusammen": "summarization",
    # Vulnerability-Scan
    "audit security": "vulnerability_scan",
    "security scan": "vulnerability_scan",
    "sicherheitsscan": "vulnerability_scan",
    "check cve": "vulnerability_scan",
}


# ── Capability Synonym Table (canonical → keywords) ──────────────────────────

_CANONICAL_CAPABILITIES: dict[str, list[str]] = {
    # 1. Code schreiben / generieren / ausführen
    "code": [
        "code", "script", "program", "python", "javascript", "typescript",
        "html", "css", "function", "klasse", "class", "module", "modul",
        "implement", "implementier", "refactor", "implementierung",
        "bugfix", "bug", "fix", "patch", "compile", "kompilier",
        "library", "bibliothek", "framework",
    ],
    "code_generation": [
        "code_generation", "codegeneration",
        "schreibcode", "writecode",
        "erstellcode", "generiercode", "generatecode", "buildcode",
        "implementierfunktion",
    ],
    "code_review": [
        "code_review", "codereview", "reviewcode",
        "reviewcodebasis", "codequality", "codequalitaet",
    ],
    "debugging": [
        "debug", "debugging", "debugge", "troubleshoot",
        "fehlerbehebung", "fehlersuche", "stacktrace", "exception",
    ],
    # 2. Texte / Schreiben / Doku
    "write": [
        "write", "schreib", "verfass", "compose", "draft",
        "erstelle", "textschreiben", "aufschreiben",
        "artikel", "blog", "slogan",
        "content", "copywriting", "textcreation",
    ],
    "content_creation": [
        "content_creation", "contentcreation", "kreativtext",
        "artikelschreib", "blogpost", "blogeintrag",
        "story", "geschichte", "creative", "kreativ",
        "textcontent", "textinhalt", "dokumentation",
    ],
    "writing": [
        "writing", "writingtask", "textaufgabe",
    ],
    # 3. Shell / Commands / Scripts ausführen
    "shell": [
        "shell", "bash", "terminal", "command", "commandline",
        "cmd", "konsole", "shellcommand", "shellkommando",
        "pytest", "unittest", "npm", "yarn", "pip",
        "runpytest", "runpytests", "executecommand", "runcommand",
        "execute", "ausfuehren", "ausführen", "lauflassen",
        "run",
    ],
    # 4. Suche / Recherche / Web
    "search": [
        "search", "suche", "find", "finde", "lookup", "nachschlag",
        "suchanfrage", "searchquery",
    ],
    "web_research": [
        "web_research", "webresearch", "research",
        "recherchier", "recherche", "researchtask",
        "factcheck", "faktencheck",
        "investigate", "investigier",
    ],
    "search_web": [
        "search_web", "websearch", "internetsearch",
        "google", "duckduckgo", "bing", "brave",
        "online_search", "onlinesearch", "webrecherche",
    ],
    "fact_checking": [
        "fact_checking", "factchecking",
    ],
    # 5. Browser / Web-Pages bedienen
    "browser": [
        "browser", "playwright", "selenium", "webdriver",
        "navigat", "navigation", "webseite", "webpage",
        "openurl", "urlopen", "click", "klick",
        "browseraction", "browser_action",
    ],
    # 6. Video / Audio
    "video": [
        "video", "film", "clip", "aufzeichnung", "recording",
        "videoschnitt", "videocreate", "videoaufnahme",
    ],
    "audio": [
        "audio", "ton", "sound", "music", "musik", "tts",
        "stimme", "voice", "speak", "sprich", "sprachausgabe",
    ],
    # 7. Analyse / Vergleichen / Bewerten
    "analysis": [
        "analysis", "analyse", "analysiere", "analyze",
        "vergleich", "compare", "evaluier", "evaluate",
        "review", "reviewen", "bewert", "beurteile",
        "vergleiche", "vergleichen", "betrachte",
    ],
    "design": [
        "design", "entwurf", "layout", "mockup", "wireframe",
        "gestaltung", "ui", "ux", "interface",
    ],
    "refactor": [
        "refactor", "refactoring", "refaktorier", "umstrukturier",
        "restructure", "umorganisier",
    ],
    "plan": [
        "plan", "planning", "planung", "strategie",
        "roadmap", "konzept", "concept", "outline",
        "gliederung", "skizzier", "skizze",
    ],
    "audit": [
        "audit", "securityaudit", "security_audit",
        "sicherheitspruefung", "sicherheitsüberprüfung",
        "schwachstelle", "schwachstellen", "vulnerability",
        "vulnerabilities", "scan", "securityscan",
    ],
    "summarize": [
        "summarize", "summariz", "zusammenfass", "kurzfass",
        "fasszusammen", "summary", "tl", "tldr",
        "recap", "recapitulate",
    ],
    "translate": [
        "translate", "uebersetz", "übersetz", "translation",
        "uebersetzung", "übersetzung", "sprachwechsel",
    ],
    # 8. File-I/O
    "file_read": [
        "file_read", "fileread", "readfile", "liesdatei",
        "datei_lesen", "datelese", "lies", "liest",
        "cat", "head", "tail", "less", "liesdatei",
    ],
    "fetch": [
        "fetch", "lade", "downloade", "download",
        "herunterlade", "abholen",
    ],
    "write_file": [
        "write_file", "writefile", "schreibdatei",
        "datei_schreiben", "savedatei", "savefile",
        "erstelledatei", "creatdatei", "createfile",
        "erzeugedatei", "datei", "erstelle",
    ],
    "edit": [
        "edit", "editing",
        "bearbeit", "bearbeite", "bearbeiten",
        "editier", "editiere", "editieren",
        "modifizier", "modifiziere", "modifizieren",
        "modify", "modification",
        "aender", "aendere", "aendern", "änder", "ändere", "ändern",
        "change", "patch", "manipulier", "manipuliere",
    ],
    "editing": [
        "editing", "lektorat", "proofread", "korrekturlesen",
        "editingtask", "refactored",
    ],
    # 9. Security / Monitoring
    "security_audit": [
        "security_audit", "securityaudit", "secscan",
        "securityscan", "securitytest", "security",
        "sicherheitscheck", "sicherheitsanalyse",
    ],
    "monitoring": [
        "monitoring", "monitor", "ueberwach", "überwach",
        "watchdog", "healthcheck", "liveness",
    ],
    # 10. Coordination / Dispatch (GeneralAG routing surface)
    "coordination": [
        "coordination", "koordiniere", "coordinate",
        "delegiere", "delegate", "verteile",
        "dispatch", "dispatchtask", "dispatch_task",
        "orchestrate", "orchestrier", "koordination",
        "taskverteilung", "koordinator",
    ],
    # 11. Profile / User-Settings (SoulAG routing surface)
    "profile_management": [
        "profile_management", "profilemanagement",
        "profil", "profile", "user-einstellungen",
        "user_settings", "usersettings", "persona",
        "soul_memory", "soulmemory",
        "kontoeinstellung", "account_settings",
    ],
    # 12. Summarization (deterministic Zusammenfassungs-Routing)
    "summarization": [
        "summarization", "zusammenfassung",
        "summary", "summarize", "summariz",
        "recap", "ueberblick", "überblick",
        "zusammenfassen", "fassezusammen",
        "tl", "tldr", "kurzfassung",
    ],
    # 13. Vulnerability-Scan (SecurityAG routing surface)
    "vulnerability_scan": [
        "vulnerability_scan", "vulnerabilityscan",
        "schwachstelle", "schwachstellen",
        "vulnerability", "vulnerabilities",
        "cve", "exploit", "exploits",
        "schwachstellenscan", "vuln_scan",
    ],
}


# ── Build lookup helpers (cached) ───────────────────────────────────────────


_exact_index: dict[str, str] = {}      # keyword → "exact:<cap>" | "synonym:<cap>"
_index_lock = threading.Lock()


def _build_indexes() -> None:
    """Baut den flachen Lookup-Index aus ``_CANONICAL_CAPABILITIES``.

    Pro Keyword wird gespeichert:
      - ``"exact:<canonical>"`` falls das Keyword exakt dem Canonical-Namen entspricht,
      - sonst ``"synonym:<canonical>"``.

    ``_resolve_capability`` liest das Präfix, um Exact von Synonym zu unterscheiden.
    """
    global _exact_index
    with _index_lock:
        if _exact_index:
            return
        for canonical, keywords in _CANONICAL_CAPABILITIES.items():
            for kw in keywords:
                kl = kw.lower()
                if kl == canonical:
                    _exact_index[kl] = "exact:" + canonical
                else:
                    # Bestehender Eintrag wird nicht überschrieben (Reihenfolge der
                    # Deklaration gewinnt) — ``exact`` ist "stärker" als ``synonym``.
                    _exact_index.setdefault(kl, "synonym:" + canonical)


_build_indexes()


# ── Tokenizer ───────────────────────────────────────────────────────────────


_TOKEN_RE = re.compile(r"[^a-z0-9äöüß]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase + non-alphanumeric split.

    Sehr einfach gehalten: keine mehrsprachige NLP, keine Stammform-
    Reduktion. Die Synonymtabelle oben enthält bereits Wortstämme
    (EN + DE), so dass ein robuster Literal-Match reicht.

    Beispiele
    ---------
    >>> _tokenize("Write a File!")
    ['write', 'a', 'file']
    >>> _tokenize("schreibe datei")
    ['schreibe', 'datei']
    """
    if not text or not isinstance(text, str):
        return []
    return [t for t in _TOKEN_RE.split(text.lower()) if t]


# ── Public Resolver API ─────────────────────────────────────────────────────


def resolve_capability(
    intent_text: str,
    available_capabilities: Optional[list[str]] = None,
) -> ResolvedCapability:
    """Bestimmt deterministisch eine Capability aus ``intent_text``.

    Parameters
    ----------
    intent_text
        Freitext-Intent (z.B. der LLM-Output eines Worker-Agents oder der
        User-Prompt). Wird via :func:`_tokenize` in Tokens zerlegt und
        gegen Phrase- und Token-Indizes gematcht.
    available_capabilities
        Optional: Liste der Capabilities, die aktuell wirklich verfügbar
        sind (z.B. aus ``agent_capabilities``-Tabelle). Wenn gesetzt, wird
        das Ergebnis auf die Whitelist gefiltert. Wenn der einzige Match
        herausgefiltert wird, produziert die Funktion einen
        ``fallback``-Hinweis (sofern ``"general"`` in der Whitelist ist).

    Returns
    -------
    ResolvedCapability
        Bei ``source == "none"`` ist ``capability == ""``. Caller müssen
        dann ``build_fallback_chain`` oder ihre eigene Heuristik verwenden.
    """
    if not intent_text or not isinstance(intent_text, str):
        return ResolvedCapability("", 0.0, "none")

    text_lower = intent_text.lower()
    tokens = _tokenize(text_lower)
    available_set: Optional[set[str]] = (
        None if available_capabilities is None
        else {c.lower() for c in available_capabilities}
    )

    # Sammelt Kandidaten, die durch den available_set-Filter gefallen sind.
    _filtered: list[str] = []

    # Pass 0: phrase-basiertes Exact-Match (längste zuerst).
    # Sortiert nach Phrasen-Länge DESC, damit "write a file" vor "write"
    # gewinnt.
    sorted_phrases = sorted(_PHRASE_PATTERNS.items(), key=lambda kv: -len(kv[0]))
    for phrase, cap in sorted_phrases:
        # Wortgrenzen-Suche — Phrasen matchen nicht innerhalb längerer Wörter.
        if re.search(r"\b" + re.escape(phrase) + r"\b", text_lower):
            if available_set is None or cap in available_set:
                return ResolvedCapability(cap, 1.0, "exact_match")
            _filtered.append(cap)

    # Pass 1: single-token-Exact (Token == Canonical-Name).
    for tok in tokens:
        hit = _exact_index.get(tok)
        if hit and hit.startswith("exact:"):
            cap = hit[len("exact:"):]
            if available_set is None or cap in available_set:
                return ResolvedCapability(cap, 1.0, "exact_match")
            _filtered.append(cap)

    # Pass 2: single-token-Synonym.
    for tok in tokens:
        hit = _exact_index.get(tok)
        if hit and hit.startswith("synonym:"):
            cap = hit[len("synonym:"):]
            if available_set is None or cap in available_set:
                return ResolvedCapability(cap, 0.7, "synonym")
            _filtered.append(cap)

    # Pass 3: Fallback — wenn (a) eine Whitelist gesetzt ist, (b) es überhaupt
    # gefilterte Matches gab, und (c) "general" in der Whitelist angeboten
    # wird, dann liefern wir "general" als schwachen Catch-All.
    if available_set is not None and _filtered and "general" in available_set:
        return ResolvedCapability("general", 0.3, "fallback")

    # Nichts gefunden — Caller muss selbst entscheiden.
    return ResolvedCapability("", 0.0, "none")


def resolve_with_node_id(
    intent_text: str,
    available_capabilities: Optional[list[str]],
    node_resolver_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> ResolvedCapability:
    """Wie :func:`resolve_capability`, aber mit Offload-Node-ID-Bridge.

    Ablauf
    ------
    1. Suche ein ``node_id``-Token (Format ``^[a-f0-9]{8}$``) in
       ``intent_text``.
    2. Wenn gefunden + ``node_resolver_fn`` ist nicht None → Inhalt über
       den Resolver laden und auf diesem Content ein zweites
       :func:`resolve_capability`-Matching laufen lassen.
    3. Wenn das einen Treffer liefert → ``source="node_id_override"``
       mit hoher Konfidenz (≥0.95).
    4. Andernfalls normales Fallback-Verhalten wie in
       :func:`resolve_capability`.

    Sicherheit: der Regex liegt in :mod:`gnom_hub.memory.offload`
    (``NODE_ID_PATTERN``) — wir greifen exakt auf diese Konstante zurück,
    damit die Bridge dieselbe Validierung wie der direkte
    ``offload_recall``-Pfad verwendet.
    """
    try:
        from gnom_hub.memory.offload import NODE_ID_PATTERN
    except Exception:  # pragma: no cover — defensive
        logger.debug("NODE_ID_PATTERN import failed; routing ohne Offload-Bridge")
        return resolve_capability(intent_text, available_capabilities)

    # NODE_ID_PATTERN ist als ``re.compile(r"^[a-f0-9]{8}$")`` definiert —
    # d.h. es matcht nur einen String, der EXAKT aus 8 Hex-Chars besteht.
    # Für den Lookup in Freitext tokenisieren wir und prüfen jeden Token via
    # ``.match()``; das respektiert die strikte Validierung.
    tokens = _tokenize(intent_text or "")
    node_id_match_str: Optional[str] = None
    for _tok in tokens:
        if NODE_ID_PATTERN.match(_tok):
            node_id_match_str = _tok
            break
    if not node_id_match_str:
        return resolve_capability(intent_text, available_capabilities)

    if node_resolver_fn is None:
        try:
            from gnom_hub.memory.node_resolver import resolve_node as _rn
            node_resolver_fn = lambda nid: _rn(nid, "default")  # type: ignore[assignment]
        except Exception:
            return resolve_capability(intent_text, available_capabilities)

    try:
        content = node_resolver_fn(node_id_match_str)
    except Exception as exc:
        logger.debug("node_resolver_fn failed for %s: %s", node_id_match_str, exc)
        content = None

    if content:
        resolved = resolve_capability(content, available_capabilities)
        if resolved.source != "none":
            return ResolvedCapability(
                capability=resolved.capability,
                confidence=max(resolved.confidence, 0.95),
                source="node_id_override",
            )

    # Fallback: normaler Pfad auf intent_text (NICHT auf dem Inhalt —
    # semantisch ist der Node-ID-Pfad ein separater Kanal).
    return resolve_capability(intent_text, available_capabilities)


# ── Fallback-Chain Builder ──────────────────────────────────────────────────


def build_fallback_chain(
    primary: str,
    available: Optional[list[str]] = None,
) -> list[str]:
    """Erzeugt eine deterministische Fallback-Kette für Routing-Dead-Ends.

    Reihenfolge
    -----------
    1. ``primary`` (z.B. die primär aufgelöste Capability).
    2. ``"general"`` (Catch-All — die meisten Agenten akzeptieren das
       als generische Fähigkeit).
    3. ``""`` (Sentinel — signalisiert "kein Routing möglich").

    Wenn ``available`` gesetzt ist, werden nur Capabilities behalten,
    die in dieser Whitelist vorkommen. Doppelte werden entfernt; die
    Reihenfolge bleibt deterministisch (kein Sort, keine Hash-Reihenfolge).

    Parameters
    ----------
    primary
        Die bevorzugte Capability.
    available
        Optionale Whitelist — wenn gesetzt, filtern wir darauf. ``""``
        (Sentinel) bleibt in jedem Fall enthalten.

    Returns
    -------
    list[str]
        Geordnete Liste. Wenn etwas gefunden wurde, endet die Liste auf
        ``""`` (Sentinel); wenn nichts gefunden wurde, ist die Liste
        ``["", ""]`` (deterministisch mindestens ein Sentinel).
    """
    chain: list[str] = []
    if primary:
        chain.append(primary)
    chain.append("general")

    if available is None:
        # Deterministische Deduplizierung behält die Reihenfolge.
        seen: set[str] = set()
        deduped: list[str] = []
        for c in chain:
            if c not in seen:
                deduped.append(c)
                seen.add(c)
        deduped.append("")  # Sentinel am Ende
        # Wenn primary und general identisch sind, sieht das aus wie ["general", ""].
        return deduped

    # available-Filter: nur Capabilities, die registriert sind.
    avail_set = {c.lower() for c in available}
    out: list[str] = []
    seen_lowered: set[str] = set()
    for c in chain:
        if not c:
            continue
        cl = c.lower()
        if cl in avail_set and cl not in seen_lowered:
            out.append(c)
            seen_lowered.add(cl)
    out.append("")
    return out


__all__ = [
    "ResolvedCapability",
    "SourceTag",
    "resolve_capability",
    "resolve_with_node_id",
    "build_fallback_chain",
]
