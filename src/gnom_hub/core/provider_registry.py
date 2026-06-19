"""Provider-Registry für Gnom-Hub.

Zentrale, ausführliche Beschreibung aller unterstützten LLM-, Web-Search- und
TTS-Provider. Wird vom SmartRouter, vom Frontend (Auto-Detect) und vom
Key-Verifier konsumiert.

Format pro Provider::

    {
      "name":                "openai",
      "display_name":        "OpenAI",
      "api_key_prefixes":    ["sk-", "sk-proj-"],
      "key_validation_endpoint": "https://api.openai.com/v1/models",
      "model_discovery_endpoint": "https://api.openai.com/v1/models",
      "capabilities":        ["chat", "vision", "image", "audio", "embedding", "tools"],
      "free_tier_supported": False,
      "notes":               "Pay-as-you-go; vision via gpt-4o family.",
    }

Public API:

- :data:`PROVIDERS`         – Dict[name, dict]
- :func:`get_provider(name)`
- :func:`get_providers_by_capability(cap)`
- :func:`get_provider_names`
- :func:`detect_provider_from_key(key)`
- :func:`detect_provider_from_label(label)`

Each entry is also exposed as a :class:`ProviderInfo` dataclass via
:func:`iter_providers`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Iterable, List, Optional


# ─── Dataclass ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProviderInfo:
    """Single source of truth for one provider.

    `field` types mirror the public dict schema documented at the top of this
    module. Pydantic isn't required at runtime — the dataclass is enough for
    type-checkers and ad-hoc ``asdict()`` serialization.
    """

    name: str
    display_name: str
    api_key_prefixes: List[str] = field(default_factory=list)
    key_validation_endpoint: str = ""
    model_discovery_endpoint: str = ""
    capabilities: List[str] = field(default_factory=list)
    free_tier_supported: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def has_capability(self, cap: str) -> bool:
        return cap in self.capabilities


# ─── Provider definitions ───────────────────────────────────────────────────
# Each tuple: (name, display_name, key_prefixes, validate_url, discover_url,
#              capabilities, free_tier, notes)
# Keep entries alphabetised within their group for readability.

_LLM_PROVIDERS: List[ProviderInfo] = [
    ProviderInfo(
        name="ai21",
        display_name="AI21 Labs",
        api_key_prefixes=["ai21-"],
        key_validation_endpoint="https://api.ai21.com/studio/v1/models",
        model_discovery_endpoint="https://api.ai21.com/studio/v1/models",
        capabilities=["chat"],
        free_tier_supported=False,
        notes="Jamba family; long-context (256k) models.",
    ),
    ProviderInfo(
        name="anthropic",
        display_name="Anthropic",
        api_key_prefixes=["sk-ant-", "sk-ant-api03-"],
        key_validation_endpoint="https://api.anthropic.com/v1/models",
        model_discovery_endpoint="https://api.anthropic.com/v1/models",
        capabilities=["chat", "vision", "tools"],
        free_tier_supported=False,
        notes="Claude 3.5/4 family. x-api-key auth header required.",
    ),
    ProviderInfo(
        name="cohere",
        display_name="Cohere",
        api_key_prefixes=["co-"],
        key_validation_endpoint="https://api.cohere.ai/v1/models",
        model_discovery_endpoint="https://api.cohere.ai/v1/models",
        capabilities=["chat", "embedding"],
        free_tier_supported=True,
        notes="Trial tier available; Command-R+ strong for RAG.",
    ),
    ProviderInfo(
        name="deepseek",
        display_name="DeepSeek",
        api_key_prefixes=["sk-"],
        key_validation_endpoint="https://api.deepseek.com/user/balance",
        model_discovery_endpoint="https://api.deepseek.com/models",
        capabilities=["chat", "tools"],
        free_tier_supported=False,
        notes="deepseek-reasoner for reasoning, deepseek-chat otherwise.",
    ),
    ProviderInfo(
        name="deepseek-coder",
        display_name="DeepSeek Coder",
        api_key_prefixes=["sk-"],
        key_validation_endpoint="https://api.deepseek.com/user/balance",
        model_discovery_endpoint="https://api.deepseek.com/models",
        capabilities=["chat", "code"],
        free_tier_supported=False,
        notes="Specialised code model — alias for deepseek with code prompt.",
    ),
    ProviderInfo(
        name="fireworks",
        display_name="Fireworks AI",
        api_key_prefixes=["fw-"],
        key_validation_endpoint="https://api.fireworks.ai/inference/v1/models",
        model_discovery_endpoint="https://api.fireworks.ai/inference/v1/models",
        capabilities=["chat", "vision", "tools", "embedding"],
        free_tier_supported=True,
        notes="$1 free credits on signup; fast inference.",
    ),
    ProviderInfo(
        name="gemini",
        display_name="Google Gemini",
        api_key_prefixes=["AIzaSy", "AIza"],
        key_validation_endpoint="https://generativelanguage.googleapis.com/v1beta/models",
        model_discovery_endpoint="https://generativelanguage.googleapis.com/v1beta/models",
        capabilities=["chat", "vision", "image", "audio", "tools", "embedding"],
        free_tier_supported=True,
        notes="Free tier with rate-limits; key passed as ?key= param.",
    ),
    ProviderInfo(
        name="google-ai-studio",
        display_name="Google AI Studio",
        api_key_prefixes=["AIza"],
        key_validation_endpoint="https://aistudio.google.com/api/models",
        model_discovery_endpoint="https://aistudio.google.com/api/models",
        capabilities=["chat", "vision"],
        free_tier_supported=True,
        notes="Web-UI friendly alias for gemini keys; same backend.",
    ),
    ProviderInfo(
        name="groq",
        display_name="Groq",
        api_key_prefixes=["gsk_"],
        key_validation_endpoint="https://api.groq.com/openai/v1/models",
        model_discovery_endpoint="https://api.groq.com/openai/v1/models",
        capabilities=["chat", "tools"],
        free_tier_supported=True,
        notes="Ultra-low-latency LPU inference; Llama & Mixtral.",
    ),
    ProviderInfo(
        name="huggingface",
        display_name="Hugging Face",
        api_key_prefixes=["hf_"],
        key_validation_endpoint="https://huggingface.co/api/whoami-v2",
        model_discovery_endpoint="https://huggingface.co/api/models",
        capabilities=["chat", "embedding", "image"],
        free_tier_supported=True,
        notes="Inference API; free tier with cold-start.",
    ),
    ProviderInfo(
        name="kimi",
        display_name="Kimi (Moonshot)",
        api_key_prefixes=["sk-"],
        key_validation_endpoint="https://api.moonshot.cn/v1/models",
        model_discovery_endpoint="https://api.moonshot.cn/v1/models",
        capabilities=["chat"],
        free_tier_supported=False,
        notes="Chinese provider (Moonshot AI); 200k context window.",
    ),
    ProviderInfo(
        name="llamacpp",
        display_name="llama.cpp (lokal)",
        api_key_prefixes=[],
        key_validation_endpoint="http://localhost:8080/health",
        model_discovery_endpoint="http://localhost:8080/v1/models",
        capabilities=["chat", "embedding"],
        free_tier_supported=True,
        notes="Local llama.cpp server; OpenAI-compatible API on :8080.",
    ),
    ProviderInfo(
        name="mistral",
        display_name="Mistral AI",
        api_key_prefixes=["sk-", "ms-"],
        key_validation_endpoint="https://api.mistral.ai/v1/models",
        model_discovery_endpoint="https://api.mistral.ai/v1/models",
        capabilities=["chat", "vision", "tools", "embedding"],
        free_tier_supported=True,
        notes="La Plateforme; codestral for code, mistral-large for general.",
    ),
    ProviderInfo(
        name="mistral-codestral",
        display_name="Mistral Codestral",
        api_key_prefixes=["sk-"],
        key_validation_endpoint="https://api.mistral.ai/v1/models",
        model_discovery_endpoint="https://api.mistral.ai/v1/models",
        capabilities=["chat", "code"],
        free_tier_supported=False,
        notes="Specialised code model from Mistral.",
    ),
    ProviderInfo(
        name="openai",
        display_name="OpenAI",
        api_key_prefixes=["sk-", "sk-proj-"],
        key_validation_endpoint="https://api.openai.com/v1/models",
        model_discovery_endpoint="https://api.openai.com/v1/models",
        capabilities=["chat", "vision", "image", "audio", "tools", "embedding"],
        free_tier_supported=False,
        notes="GPT-4o family; vision via gpt-4o; o1 for reasoning.",
    ),
    ProviderInfo(
        name="opencode",
        display_name="OpenCode Zen",
        api_key_prefixes=["sk-ec", "sk-opencode"],
        key_validation_endpoint="https://opencode.ai/zen/v1/models",
        model_discovery_endpoint="https://opencode.ai/zen/v1/models",
        capabilities=["chat", "tools"],
        free_tier_supported=False,
        notes="Zen catalogue; Claude & GPT models behind one key.",
    ),
    ProviderInfo(
        name="ollama",
        display_name="Ollama (lokal)",
        api_key_prefixes=[],
        key_validation_endpoint="http://localhost:11434/api/tags",
        model_discovery_endpoint="http://localhost:11434/api/tags",
        capabilities=["chat", "vision", "embedding"],
        free_tier_supported=True,
        notes="Local-first; no key required, runs on :11434 by default.",
    ),
    ProviderInfo(
        name="openrouter",
        display_name="OpenRouter",
        api_key_prefixes=["sk-or-", "sk-or-v1-"],
        key_validation_endpoint="https://openrouter.ai/api/v1/key",
        model_discovery_endpoint="https://openrouter.ai/api/v1/models",
        capabilities=["chat", "vision", "tools", "embedding"],
        free_tier_supported=True,
        notes="Aggregator with many free-tier models (':free' suffix).",
    ),
    ProviderInfo(
        name="perplexity",
        display_name="Perplexity",
        api_key_prefixes=["pplx-"],
        key_validation_endpoint="https://api.perplexity.ai/v1/models",
        model_discovery_endpoint="https://api.perplexity.ai/v1/models",
        capabilities=["chat", "web"],
        free_tier_supported=False,
        notes="Online search baked-in; Sonar models.",
    ),
    ProviderInfo(
        name="replicate",
        display_name="Replicate",
        api_key_prefixes=["r8_"],
        key_validation_endpoint="https://api.replicate.com/v1/account",
        model_discovery_endpoint="https://api.replicate.com/v1/models",
        capabilities=["chat", "image", "audio", "embedding"],
        free_tier_supported=True,
        notes="Pay-per-second; runs open-source models via Cog.",
    ),
    ProviderInfo(
        name="together",
        display_name="Together AI",
        api_key_prefixes=["together-"],
        key_validation_endpoint="https://api.together.xyz/v1/models",
        model_discovery_endpoint="https://api.together.xyz/v1/models",
        capabilities=["chat", "vision", "tools", "embedding", "image"],
        free_tier_supported=True,
        notes="$5 free credits; wide open-source model catalogue.",
    ),
    ProviderInfo(
        name="xai",
        display_name="xAI (Grok)",
        api_key_prefixes=["xai-"],
        key_validation_endpoint="https://api.x.ai/v1/api-key",
        model_discovery_endpoint="https://api.x.ai/v1/models",
        capabilities=["chat", "vision", "tools"],
        free_tier_supported=False,
        notes="Grok family; OpenAI-compatible chat endpoint.",
    ),
    ProviderInfo(
        name="minimax",
        display_name="MiniMax",
        api_key_prefixes=["sk-cp-"],
        key_validation_endpoint="https://api.minimax.io/v1/models",
        model_discovery_endpoint="https://api.minimax.io/v1/models",
        capabilities=["chat", "vision", "image", "audio", "video", "music", "tools"],
        free_tier_supported=False,
        notes="MiniMax M3 default model; stop sequence 深思 to prevent runaway. "
              "Multimodal API: gleicher Key deckt Text, Vision, Bild-/Audio-/Video-/Musik-Generierung ab.",
    ),
]

_WEB_SEARCH_PROVIDERS: List[ProviderInfo] = [
    ProviderInfo(
        name="brave",
        display_name="Brave Search",
        api_key_prefixes=["BSA", "BS-"],
        key_validation_endpoint="https://api.search.brave.com/res/v1/web/search?q=ping",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=True,
        notes="2 000 queries/month free; X-Subscription-Token header.",
    ),
    ProviderInfo(
        name="tavily",
        display_name="Tavily",
        api_key_prefixes=["tvly-"],
        key_validation_endpoint="https://api.tavily.com/search",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=True,
        notes="Optimised for LLM agents; 1 000 searches/month free.",
    ),
    ProviderInfo(
        name="serper",
        display_name="Serper (Google SERP)",
        api_key_prefixes=["serper-"],
        key_validation_endpoint="https://google.serper.dev/search",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=False,
        notes="Google search results; 50 credits on signup.",
    ),
    ProviderInfo(
        name="serpng",
        display_name="SerpNG",
        api_key_prefixes=["serpng-"],
        key_validation_endpoint="https://serpapi.com/search.json",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=False,
        notes="Affordable Google SERP scraping.",
    ),
    ProviderInfo(
        name="google-cse",
        display_name="Google Custom Search",
        api_key_prefixes=["AIzaSy"],
        key_validation_endpoint="https://www.googleapis.com/customsearch/v1?q=test",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=True,
        notes="100 queries/day free; requires separate CX id.",
    ),
    ProviderInfo(
        name="bing-search",
        display_name="Bing Web Search",
        api_key_prefixes=[],
        key_validation_endpoint="https://api.bing.microsoft.com/v7.0/search?q=test",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=True,
        notes="1 000 queries/month free tier via Azure.",
    ),
    ProviderInfo(
        name="duckduckgo",
        display_name="DuckDuckGo",
        api_key_prefixes=[],
        key_validation_endpoint="https://duckduckgo.com/?q=test&format=json",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=True,
        notes="No key required; rate-limited.",
    ),
    ProviderInfo(
        name="you-com",
        display_name="You.com",
        api_key_prefixes=["you-"],
        key_validation_endpoint="https://api.you.com/v1/search",
        model_discovery_endpoint="",
        capabilities=["web_search", "chat"],
        free_tier_supported=True,
        notes="Search + Smart Agent endpoints.",
    ),
    ProviderInfo(
        name="kagi",
        display_name="Kagi Search",
        api_key_prefixes=["kagi-"],
        key_validation_endpoint="https://kagi.com/api/v0/search",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=False,
        notes="Premium search; high-quality results, paid only.",
    ),
    ProviderInfo(
        name="exa",
        display_name="Exa (Metaphor)",
        api_key_prefixes=["exa-"],
        key_validation_endpoint="https://api.exa.ai/search",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=True,
        notes="Neural search; 1 000 queries/month free.",
    ),
    ProviderInfo(
        name="perplexity-search",
        display_name="Perplexity Search",
        api_key_prefixes=["pplx-"],
        key_validation_endpoint="https://api.perplexity.ai/v1/models",
        model_discovery_endpoint="https://api.perplexity.ai/v1/models",
        capabilities=["web_search", "chat"],
        free_tier_supported=False,
        notes="Online search via Sonar models — share key with perplexity chat.",
    ),
]

_TTS_PROVIDERS: List[ProviderInfo] = [
    ProviderInfo(
        name="elevenlabs",
        display_name="ElevenLabs",
        api_key_prefixes=["sk_"],
        key_validation_endpoint="https://api.elevenlabs.io/v1/user",
        model_discovery_endpoint="https://api.elevenlabs.io/v1/models",
        capabilities=["tts"],
        free_tier_supported=True,
        notes="10 000 characters/month free; voice cloning.",
    ),
    ProviderInfo(
        name="openai-tts",
        display_name="OpenAI TTS",
        api_key_prefixes=["sk-", "sk-proj-"],
        key_validation_endpoint="https://api.openai.com/v1/models",
        model_discovery_endpoint="https://api.openai.com/v1/models",
        capabilities=["tts", "audio"],
        free_tier_supported=False,
        notes="tts-1 / tts-1-hd voices; share key with OpenAI chat.",
    ),
    ProviderInfo(
        name="edge-tts",
        display_name="Microsoft Edge TTS",
        api_key_prefixes=[],
        key_validation_endpoint="https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list",
        model_discovery_endpoint="",
        capabilities=["tts"],
        free_tier_supported=True,
        notes="Free, no key needed; runs via edge-tts Python lib.",
    ),
    ProviderInfo(
        name="google-tts",
        display_name="Google Cloud TTS",
        api_key_prefixes=["AIza"],
        key_validation_endpoint="https://texttospeech.googleapis.com/v1/voices",
        model_discovery_endpoint="https://texttospeech.googleapis.com/v1/voices",
        capabilities=["tts", "audio"],
        free_tier_supported=True,
        notes="Standard & WaveNet voices; 4M characters free per month.",
    ),
    ProviderInfo(
        name="azure-tts",
        display_name="Azure TTS",
        api_key_prefixes=[],
        key_validation_endpoint="https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
        model_discovery_endpoint="",
        capabilities=["tts", "audio"],
        free_tier_supported=True,
        notes="500 000 characters/month free; needs region+endpoint in env.",
    ),
    ProviderInfo(
        name="playht",
        display_name="PlayHT",
        api_key_prefixes=["play-"],
        key_validation_endpoint="https://api.play.ht/api/v2/voices",
        model_discovery_endpoint="https://api.play.ht/api/v2/voices",
        capabilities=["tts"],
        free_tier_supported=True,
        notes="Voice cloning; 12 500 characters free tier.",
    ),
    ProviderInfo(
        name="lmnt",
        display_name="LMNT",
        api_key_prefixes=["lmnt-"],
        key_validation_endpoint="https://api.lmnt.com/v1/voices",
        model_discovery_endpoint="https://api.lmnt.com/v1/voices",
        capabilities=["tts"],
        free_tier_supported=True,
        notes="Fast streaming TTS; generous free tier.",
    ),
    ProviderInfo(
        name="coqui",
        display_name="Coqui TTS",
        api_key_prefixes=[],
        key_validation_endpoint="https://app.coqui.ai/api/v2/voices",
        model_discovery_endpoint="",
        capabilities=["tts"],
        free_tier_supported=True,
        notes="OSS-first; hosted tier via app.coqui.ai.",
    ),
    ProviderInfo(
        name="cartesia",
        display_name="Cartesia",
        api_key_prefixes=["cartesia-"],
        key_validation_endpoint="https://api.cartesia.ai/voices",
        model_discovery_endpoint="https://api.cartesia.ai/voices",
        capabilities=["tts"],
        free_tier_supported=True,
        notes="Ultra-low-latency TTS; streaming-first.",
    ),
]

_OTHER_PROVIDERS: List[ProviderInfo] = [
    ProviderInfo(
        name="elevenlabs",
        display_name="ElevenLabs",
        api_key_prefixes=["sk_"],
        key_validation_endpoint="https://api.elevenlabs.io/v1/user",
        model_discovery_endpoint="https://api.elevenlabs.io/v1/models",
        capabilities=["tts"],
        free_tier_supported=True,
        notes="Convenience alias; primary ElevenLabs entry above.",
    ),
    ProviderInfo(
        name="brave",
        display_name="Brave Search",
        api_key_prefixes=["BSA", "BS-"],
        key_validation_endpoint="https://api.search.brave.com/res/v1/web/search?q=ping",
        model_discovery_endpoint="",
        capabilities=["web_search"],
        free_tier_supported=True,
        notes="Convenience alias; primary Brave entry above.",
    ),
    ProviderInfo(
        name="github",
        display_name="GitHub",
        api_key_prefixes=["ghp_", "gho_", "ghs_", "ghu_", "ghr_"],
        key_validation_endpoint="https://api.github.com/user",
        model_discovery_endpoint="https://api.github.com/user",
        capabilities=["code"],
        free_tier_supported=True,
        notes="Fine-grained PAT recommended; 5 000 req/hour.",
    ),
    ProviderInfo(
        name="minimax",
        display_name="MiniMax",
        api_key_prefixes=["sk-cp-"],
        key_validation_endpoint="https://api.minimax.io/v1/models",
        model_discovery_endpoint="https://api.minimax.io/v1/models",
        capabilities=["chat", "vision", "image", "audio", "video", "music", "tools"],
        free_tier_supported=False,
        notes="Convenience alias; primary MiniMax entry above. Multimodal (Text/Vision/Image/Audio/Video/Music).",
    ),
]


def _all_providers() -> List[ProviderInfo]:
    """Flatten the per-category lists, deduping by name (first wins)."""
    seen = set()
    out: List[ProviderInfo] = []
    for lst in (_LLM_PROVIDERS, _WEB_SEARCH_PROVIDERS, _TTS_PROVIDERS, _OTHER_PROVIDERS):
        for p in lst:
            if p.name in seen:
                continue
            seen.add(p.name)
            out.append(p)
    return out


# ─── Public dict & helpers ──────────────────────────────────────────────────

PROVIDERS: Dict[str, dict] = {p.name: p.to_dict() for p in _all_providers()}


def get_provider(name: str) -> Optional[dict]:
    """Return the provider dict for *name* or ``None`` if unknown."""
    p = PROVIDERS.get(name)
    return dict(p) if p else None


def get_providers_by_capability(cap: str) -> List[dict]:
    """Return all providers that advertise *cap* (e.g. ``"chat"``, ``"web_search"``)."""
    return [
        info.to_dict() for info in _all_providers()
        if cap in info.capabilities
    ]


def get_provider_names() -> List[str]:
    """Return the list of registered provider names."""
    return list(PROVIDERS.keys())


def iter_providers() -> Iterable[ProviderInfo]:
    """Iterate over the full provider list as :class:`ProviderInfo` dataclasses."""
    yield from _all_providers()


def detect_provider_from_key(key: str) -> Optional[str]:
    """Auto-detect the provider from a key prefix.

    Picks the longest matching prefix across all registered providers so a
    more specific prefix (``sk-or-``, ``sk-ant-``, ``gsk_`` …) wins over the
    generic ``sk-`` fallback. Returns ``None`` when nothing matches.
    """
    if not isinstance(key, str):
        return None
    best_name: Optional[str] = None
    best_len = 0
    for info in _all_providers():
        for prefix in info.api_key_prefixes:
            if not prefix:
                continue
            if key.startswith(prefix) and len(prefix) > best_len:
                best_name = info.name
                best_len = len(prefix)
    return best_name


def detect_provider_from_label(label: str) -> Optional[str]:
    """Heuristic provider detection from an env-var label.

    Used for ``.env`` files where the key isn't visible (``KEY=…``) but the
    variable name is (e.g. ``ANTHROPIC_API_KEY``, ``GEMINI_API_KEY``). Falls
    back to ``None`` when no match is found.
    """
    if not isinstance(label, str):
        return None
    label_l = label.lower()
    table = {
        "openai": "openai",
        "gpt": "openai",
        "chatgpt": "openai",
        "openrouter": "openrouter",
        "or_key": "openrouter",
        "anthropic": "anthropic",
        "claude": "anthropic",
        "gemini": "gemini",
        "google": "gemini",
        "ai_studio": "gemini",
        "aistudio": "gemini",
        "vertex": "gemini",
        "deepseek": "deepseek",
        "mistral": "mistral",
        "mixtral": "mistral",
        "kimi": "kimi",
        "moonshot": "kimi",
        "elevenlabs": "elevenlabs",
        "eleven": "elevenlabs",
        "tts": "elevenlabs",
        "brave": "brave",
        "search": "brave",
        "tavily": "tavily",
        "serpapi": "serper",
        "serper": "serper",
        "bing": "bing-search",
        "azure-search": "bing-search",
        "google_search": "google-cse",
        "google-search": "google-cse",
        "cse": "google-cse",
        "duckduckgo": "duckduckgo",
        "ddg": "duckduckgo",
        "you": "you-com",
        "kagi": "kagi",
        "exa": "exa",
        "metaphor": "exa",
        "github": "github",
        "gh-": "github",
        "groq": "groq",
        "cohere": "cohere",
        "perplexity": "perplexity",
        "pplx": "perplexity",
        "together": "together",
        "fireworks": "fireworks",
        "replicate": "replicate",
        "huggingface": "huggingface",
        "hf_": "huggingface",
        "ai21": "ai21",
        "jamba": "ai21",
        "xai": "xai",
        "grok": "xai",
        "ollama": "ollama",
        "llamacpp": "llamacpp",
        "llama_cpp": "llamacpp",
        "opencode": "opencode",
        "zen": "opencode",
        "playht": "playht",
        "lmnt": "lmnt",
        "cartesia": "cartesia",
        "coqui": "coqui",
        "edge-tts": "edge-tts",
        "google-tts": "google-tts",
        "azure-tts": "azure-tts",
        "minimax": "minimax",
        "sk-cp-": "minimax",
    }
    # Longest match wins.
    best = None
    best_len = 0
    for needle, pid in table.items():
        if needle and needle in label_l and len(needle) > best_len:
            best = pid
            best_len = len(needle)
    return best


__all__ = [
    "ProviderInfo",
    "PROVIDERS",
    "get_provider",
    "get_providers_by_capability",
    "get_provider_names",
    "iter_providers",
    "detect_provider_from_key",
    "detect_provider_from_label",
]
