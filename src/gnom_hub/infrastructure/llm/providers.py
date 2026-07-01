"""Zentrale Provider-Registry für Gnom-Hub.

Single source of truth für:
- Backend (key_verifier.py): API-Endpoints + Auth-Header
- Frontend (dashboard.js): labelToProvider() Mappings
- Router (router_config.py): bevorzugte Modelle pro Provider

Bei neuen Providern: HIER hinzufügen, dann überall verfügbar.

Format pro Provider:
{
  "id": "openai",                       # Kurz-Name (vom Backend verwendet)
  "display_name": "OpenAI",             # Anzeige im Frontend
  "caps": ["text", "vision", ...],      # Was kann der Provider?
  "test_url": "https://...",            # GET-Endpoint um Key zu validieren
  "test_method": "GET",                 # HTTP-Methode für Test
  "test_headers": {"Authorization": "Bearer {key}"},  # Header-Template
  "key_prefixes": ["sk-", "sk-proj-"], # Auto-detect Patterns
  "label_patterns": ["openai", "gpt"],  # Match in KEY-LABELS (z.B. OPENAI_API_KEY)
}
"""

PROVIDERS = {
    # ─── Major LLM Providers ────────────────────────────────────
    "openai": {
        "id": "openai",
        "display_name": "OpenAI",
        "caps": ["text", "vision", "image", "audio", "tools"],
        "test_url": "https://api.openai.com/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-", "sk-proj-"],
        "label_patterns": ["openai", "gpt", "chatgpt"],
    },
    "openrouter": {
        "id": "openrouter",
        "display_name": "OpenRouter",
        "caps": ["text", "vision", "tools"],
        "test_url": "https://openrouter.ai/api/v1/key",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-or-", "sk-or-v1-"],
        "label_patterns": ["openrouter", "or_key", "or-v1"],
    },
    "anthropic": {
        "id": "anthropic",
        "display_name": "Anthropic",
        "caps": ["text", "vision", "tools"],
        "test_url": "https://api.anthropic.com/v1/models",
        "test_method": "GET",
        "test_headers": {"x-api-key": "{key}", "anthropic-version": "2023-06-01"},
        "key_prefixes": ["sk-ant-", "sk-ant-api03-"],
        "label_patterns": ["anthropic", "claude"],
    },
    "gemini": {
        "id": "gemini",
        "display_name": "Google Gemini",
        "caps": ["text", "vision", "image", "audio", "tools"],
        "test_url": "https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": ["AIzaSy", "AIza"],
        "label_patterns": ["gemini", "google", "ai_studio", "aistudio", "vertex", "bard"],
    },
    "deepseek": {
        "id": "deepseek",
        "display_name": "DeepSeek",
        "caps": ["text", "tools"],
        "test_url": "https://api.deepseek.com/user/balance",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-"],
        "label_patterns": ["deepseek", "deep-seek"],
    },
    "mistral": {
        "id": "mistral",
        "display_name": "Mistral",
        "caps": ["text", "vision", "tools"],
        "test_url": "https://api.mistral.ai/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-", "ms-"],
        "label_patterns": ["mistral", "mixtral"],
    },
    "minimax": {
        "id": "minimax",
        "display_name": "MiniMax",
        "caps": ["text", "vision", "image", "audio", "video", "music", "tools"],
        "test_url": "https://api.minimax.io/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-cp-"],
        "label_patterns": ["minimax"],
        # MiniMax-M3 ist multimodal (text + vision + tools). Über die gleiche
        # API-Key laufen Text, Vision, Bild-Generierung, Audio/TTS, Video
        # und Musik — siehe AGENT_BACKGROUNDS / backend endpoints.
    },
    "opencode-zen": {
        "id": "opencode-zen",
        "display_name": "OpenCode Zen (Claude)",
        "caps": ["text", "vision", "tools"],
        "test_url": "https://opencode.ai/zen/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-ec", "sk-opencode"],
        "label_patterns": ["opencode", "zen", "opencode-zen"],
    },
    "groq": {
        "id": "groq",
        "display_name": "Groq",
        "caps": ["text", "tools"],
        "test_url": "https://api.groq.com/openai/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["gsk_"],
        "label_patterns": ["groq"],
    },
    "cohere": {
        "id": "cohere",
        "display_name": "Cohere",
        "caps": ["text", "tools"],
        "test_url": "https://api.cohere.ai/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["co-"],
        "label_patterns": ["cohere"],
    },
    "perplexity": {
        "id": "perplexity",
        "display_name": "Perplexity",
        "caps": ["text", "tools"],
        "test_url": "https://api.perplexity.ai/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["pplx-"],
        "label_patterns": ["perplexity", "pplx"],
    },
    "together": {
        "id": "together",
        "display_name": "Together AI",
        "caps": ["text", "vision", "tools"],
        "test_url": "https://api.together.xyz/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["together-"],
        "label_patterns": ["together"],
    },
    "fireworks": {
        "id": "fireworks",
        "display_name": "Fireworks AI",
        "caps": ["text", "vision", "tools"],
        "test_url": "https://api.fireworks.ai/inference/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["fw-"],
        "label_patterns": ["fireworks"],
    },
    "replicate": {
        "id": "replicate",
        "display_name": "Replicate",
        "caps": ["text", "image", "tools"],
        "test_url": "https://api.replicate.com/v1/account",
        "test_method": "GET",
        "test_headers": {"Authorization": "Token {key}"},
        "key_prefixes": ["r8_"],
        "label_patterns": ["replicate"],
    },
    "huggingface": {
        "id": "huggingface",
        "display_name": "Hugging Face",
        "caps": ["text", "vision", "tools"],
        "test_url": "https://huggingface.co/api/whoami-v2",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["hf_"],
        "label_patterns": ["huggingface", "hugging-face", "hf_"],
    },
    "openrouter-minimax": {
        "id": "minimax",  # Routes via OpenRouter
        "display_name": "MiniMax (via OpenRouter)",
        "caps": ["text", "tools"],
        "test_url": "https://openrouter.ai/api/v1/key",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-or-v1-"],
        "label_patterns": [],
    },
    "kimi": {
        "id": "kimi",
        "display_name": "Kimi (Moonshot)",
        "caps": ["text", "tools"],
        "test_url": "https://api.moonshot.cn/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-"],
        "label_patterns": ["kimi", "moonshot", "moon"],
    },

    # ─── Audio / TTS / STT ──────────────────────────────────────
    "elevenlabs": {
        "id": "elevenlabs",
        "display_name": "ElevenLabs",
        "caps": ["audio"],
        "test_url": "https://api.elevenlabs.io/v1/user",
        "test_method": "GET",
        "test_headers": {"xi-api-key": "{key}"},
        "key_prefixes": ["sk_"],
        "label_patterns": ["elevenlabs", "eleven", "tts"],
    },
    "openai_audio": {
        "id": "openai",
        "display_name": "OpenAI Audio (TTS/STT)",
        "caps": ["audio"],
        "test_url": "https://api.openai.com/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-"],
        "label_patterns": ["tts", "whisper", "audio"],
    },

    # ─── Web Search / Research ──────────────────────────────────
    "brave": {
        "id": "brave",
        "display_name": "Brave Search",
        "caps": ["web"],
        "test_url": "https://api.search.brave.com/res/v1/web/search?q=ping",
        "test_method": "GET",
        "test_headers": {"Accept": "application/json", "X-Subscription-Token": "{key}"},
        "key_prefixes": ["BSA", "BS-"],
        "label_patterns": ["brave", "search"],
    },
    "tavily": {
        "id": "tavily",
        "display_name": "Tavily Search",
        "caps": ["web"],
        "test_url": "https://api.tavily.com/search",
        "test_method": "POST",
        "test_headers": {},
        "key_prefixes": ["tvly-"],
        "label_patterns": ["tavily"],
    },
    "serpapi": {
        "id": "serpapi",
        "display_name": "SerpAPI",
        "caps": ["web"],
        "test_url": "https://serpapi.com/account",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": ["serp-"],
        "label_patterns": ["serpapi", "serp"],
    },
    "bing": {
        "id": "bing",
        "display_name": "Bing Search",
        "caps": ["web"],
        "test_url": "https://api.bing.microsoft.com/v7.0/search?q=test",
        "test_method": "GET",
        "test_headers": {"Ocp-Apim-Subscription-Key": "{key}"},
        "key_prefixes": [],
        "label_patterns": ["bing", "azure-search"],
    },
    "google_search": {
        "id": "google_search",
        "display_name": "Google Custom Search",
        "caps": ["web"],
        "test_url": "https://www.googleapis.com/customsearch/v1?q=test&key={key}",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": ["AIzaSy"],
        "label_patterns": ["google_search", "google-search", "cse"],
    },
    "serper": {
        "id": "serper",
        "display_name": "Serper.dev",
        "caps": ["web"],
        "test_url": "https://google.serper.dev/search",
        "test_method": "POST",
        "test_headers": {"X-API-KEY": "{key}", "Content-Type": "application/json"},
        "key_prefixes": ["serp-"],
        "label_patterns": ["serper"],
    },
    "bing-search": {
        "id": "bing-search",
        "display_name": "Bing Web Search",
        "caps": ["web"],
        "test_url": "https://api.bing.microsoft.com/v7.0/search?q=test",
        "test_method": "GET",
        "test_headers": {"Ocp-Apim-Subscription-Key": "{key}"},
        "key_prefixes": [],
        "label_patterns": ["bing-search", "bing_search"],
    },
    "duckduckgo": {
        "id": "duckduckgo",
        "display_name": "DuckDuckGo (no key)",
        "caps": ["web"],
        "test_url": "https://duckduckgo.com/?q=test",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": [],
        "label_patterns": ["duckduckgo", "ddg"],
    },
    "you-com": {
        "id": "you-com",
        "display_name": "You.com Search",
        "caps": ["web"],
        "test_url": "https://api.ydc-index.io/search?query=test",
        "test_method": "GET",
        "test_headers": {"X-API-Key": "{key}"},
        "key_prefixes": [],
        "label_patterns": ["you.com", "you-com", "youdotcom"],
    },
    "kagi": {
        "id": "kagi",
        "display_name": "Kagi Search",
        "caps": ["web"],
        "test_url": "https://kagi.com/api/v0/search?q=test",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bot {key}"},
        "key_prefixes": [],
        "label_patterns": ["kagi"],
    },
    "exa": {
        "id": "exa",
        "display_name": "Exa Search",
        "caps": ["web"],
        "test_url": "https://api.exa.ai/search",
        "test_method": "POST",
        "test_headers": {"x-api-key": "{key}", "Content-Type": "application/json"},
        "key_prefixes": [],
        "label_patterns": ["exa"],
    },
    "perplexity-search": {
        "id": "perplexity-search",
        "display_name": "Perplexity Search API",
        "caps": ["web", "text"],
        "test_url": "https://api.perplexity.ai/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["pplx-"],
        "label_patterns": ["perplexity-search", "sonar"],
    },
    "edge-tts": {
        "id": "edge-tts",
        "display_name": "Microsoft Edge TTS (no key)",
        "caps": ["audio"],
        "test_url": "https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list?trustedclient=true",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": [],
        "label_patterns": ["edge-tts", "edge_tts", "ms-tts"],
    },
    "google-tts": {
        "id": "google-tts",
        "display_name": "Google Cloud TTS",
        "caps": ["audio"],
        "test_url": "https://texttospeech.googleapis.com/v1/voices?key={key}",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": ["AIzaSy"],
        "label_patterns": ["google-tts", "google_tts", "gc-tts"],
    },
    "azure-tts": {
        "id": "azure-tts",
        "display_name": "Azure Speech TTS",
        "caps": ["audio"],
        "test_url": "https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
        "test_method": "GET",
        "test_headers": {"Ocp-Apim-Subscription-Key": "{key}"},
        "key_prefixes": [],
        "label_patterns": ["azure-tts", "azure_tts", "azure-speech"],
    },
    "playht": {
        "id": "playht",
        "display_name": "PlayHT",
        "caps": ["audio"],
        "test_url": "https://api.play.ht/api/v2/voices",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": [],
        "label_patterns": ["playht", "play-ht"],
    },
    "lmnt": {
        "id": "lmnt",
        "display_name": "LMNT",
        "caps": ["audio"],
        "test_url": "https://api.lmnt.com/v1/voices",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": [],
        "label_patterns": ["lmnt"],
    },
    "coqui": {
        "id": "coqui",
        "display_name": "Coqui TTS (lokal)",
        "caps": ["audio"],
        "test_url": "http://localhost:5002/api/voices",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": [],
        "label_patterns": ["coqui", "coqui-tts"],
    },
    "cartesia": {
        "id": "cartesia",
        "display_name": "Cartesia TTS",
        "caps": ["audio"],
        "test_url": "https://api.cartesia.ai/voices",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": [],
        "label_patterns": ["cartesia"],
    },
    "openai-tts": {
        "id": "openai-tts",
        "display_name": "OpenAI TTS",
        "caps": ["audio"],
        "test_url": "https://api.openai.com/v1/models",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-"],
        "label_patterns": ["openai-tts", "openai_tts"],
    },

    # ─── Other / Special ─────────────────────────────────────────
    "github": {
        "id": "github",
        "display_name": "GitHub",
        "caps": ["code"],
        "test_url": "https://api.github.com/user",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["ghp_", "gho_", "ghs_", "ghu_", "ghr_"],
        "label_patterns": ["github", "gh-"],
    },
    "replicate_old": {
        "id": "replicate",
        "display_name": "Replicate (alt)",
        "caps": ["image"],
        "test_url": "https://api.replicate.com/v1/account",
        "test_method": "GET",
        "test_headers": {"Authorization": "Token {key}"},
        "key_prefixes": [],
        "label_patterns": [],
    },
    "ollama": {
        "id": "ollama",
        "display_name": "Ollama (lokal)",
        "caps": ["text", "vision", "tools"],
        "test_url": "http://localhost:11434/api/tags",
        "test_method": "GET",
        "test_headers": {},
        "key_prefixes": [],
        "label_patterns": ["ollama"],
    },
    "stability": {
        "id": "stability",
        "display_name": "Stability AI",
        "caps": ["image"],
        "test_url": "https://api.stability.ai/v1/user/account",
        "test_method": "GET",
        "test_headers": {"Authorization": "Bearer {key}"},
        "key_prefixes": ["sk-"],
        "label_patterns": ["stability", "stable-diffusion", "sdxl"],
    },
}


def get_provider_ids() -> list:
    """Alle Provider-IDs."""
    return list(PROVIDERS.keys())


def build_test_request(provider_id: str, key: str) -> dict:
    """Returns {url, method, headers} for testing a key."""
    p = PROVIDERS.get(provider_id)
    if not p:
        return None
    headers = {h: v.format(key=key) for h, v in p["test_headers"].items()}
    url = p["test_url"].format(key=key) if "{key}" in p["test_url"] else p["test_url"]
    return {"url": url, "method": p["test_method"], "headers": headers}


def detect_provider_from_key(key: str) -> str | None:
    """Auto-detect provider based on key prefix.

    WICHTIG: Wenn mehrere Provider mit dem Key prefix-matches haben, gewinnt
    der SPEZIFISCHSTE Prefix (längster Match), nicht der erste im dict. Das
    verhindert dass `sk-` (openai/deepseek/mistral/kimi) jeden `sk-cp-*` (MiniMax),
    `sk-or-*` (OpenRouter) oder `sk-ant-*` (Anthropic) Key fälschlich als openai
    klassifiziert — was zu 401-Fehlern und nicht persistierten Keys führte.
    """
    if not key:
        return None
    best_pid, best_len = None, 0
    for pid, p in PROVIDERS.items():
        for prefix in p["key_prefixes"]:
            if not prefix:
                continue
            if key.startswith(prefix) and len(prefix) > best_len:
                best_pid, best_len = pid, len(prefix)
    return best_pid


def detect_provider_from_label(label: str) -> str | None:
    """Auto-detect provider based on env-var label (e.g. OPENAI_API_KEY)."""
    letter = label.lower()
    for pid, p in PROVIDERS.items():
        for pattern in p["label_patterns"]:
            if pattern and pattern in letter:
                return pid
    return None
