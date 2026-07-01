
# ── Prozess-Management ─────────────────────────────────────────────────────
PROCESS_TERMINATE_TIMEOUT = 2
PROCESS_KILL_SLEEP = 1
PID_FILE_PATTERNS = ["agents.run_agent", "agents.[a-z]+AG"]

# ── Agent-Basis ────────────────────────────────────────────────────────────
AGENT_POLL_INTERVAL = 5
AGENT_SEEN_MAX = 1000
AGENT_HTTP_TIMEOUT = 10
AGENT_FETCH_TIMEOUT = 3.0
AGENT_CHAT_HISTORY_LIMIT = 20
AGENT_PROCESSING_TIMEOUT = 600
AGENT_POLL_SLEEP = 0.5

# ── Swarm / Backpressure ───────────────────────────────────────────────────
MAX_DEPTH = 8
MAX_CONCURRENT = 8
RETRY_MAX = 3
RETRY_BACKOFF_BASE = 3.0
MAX_QUEUE_DEPTH = 30
DEPENDENCY_TIMEOUT = 120.0
DEPENDENCY_POLL_S = 1.0
STUCK_MESSAGE_TIMEOUT = 300.0
WORKER_COMPLETION_TIMEOUT = 180.0
MAX_COORDINATION_ROUNDS = 4
MIN_JOBS_THRESHOLD = 5

PRIORITY_MAPPING = {
    "critical": 1,
    "high": 3,
    "normal": 5,
    "low": 7,
}

# ── Workflow ────────────────────────────────────────────────────────────────
WORKFLOW_MAX_RETRIES = 2
WORKFLOW_RETRY_DELAY = 30.0
WORKFLOW_STUCK_TIMEOUT = 300.0
WORKFLOW_MIN_SAMPLES = 3
WORKFLOW_TOP_PATTERNS = 5
WORKFLOW_SUMMARY_LIMIT = 10

# ── Soul / Gedächtnis ──────────────────────────────────────────────────────
MAX_SOUL_FACTS = 100
MIN_VALUE_LENGTH = 15
DEDUP_THRESHOLD = 0.85
HIGH_PRIO_MAX_AGE_DAYS = 30
MED_PRIO_MAX_AGE_DAYS = 14
LOW_PRIO_MAX_AGE_DAYS = 7
CLEANUP_INTERVAL = 3600
SOUL_CACHE_TTL = 300
SOUL_CACHE_MAX = 200
SOUL_HASH_SEEN_MAX = 500
SOUL_HASH_DEDUP_SECONDS = 15
SOUL_USER_SAMPLE_RATE = 65
SOUL_TOP_K_DEFAULT = 6
SOUL_INJECTIONS_MAX = 2000
SOUL_INJECTIONS_TRIM = 1000
SOUL_DIRECTIVE_TTL = 3600
SOUL_SILENT_ROUNDS = 5
MEMORY_STRENGTH_MAP = {1: 2, 2: 4, 3: 6, 4: 8, 5: 12}
EMB_CACHE_MAX_SIZE = 5000
EMB_CACHE_SAVE_EVERY = 50

# ── SMR (Semantic Memory Retrieval) ─────────────────────────────────────────
SMR_SIMILARITY_THRESHOLD = 0.60
SMR_HIGH_PRIO_WEIGHT = 1.3
SMR_LOW_PRIO_WEIGHT = 0.7
SMR_DEFAULT_WEIGHT = 1.0
SMR_TOP_K_DEFAULT = 8
SMR_PRUNE_THRESHOLD = 0.15
SMR_PRUNE_MIN_AGE_DAYS = 30

# ── HTTP Timeouts ──────────────────────────────────────────────────────────
HTTP_SHORT_TIMEOUT = 2.0
HTTP_MEDIUM_TIMEOUT = 5.0
HTTP_DEFAULT_TIMEOUT = 10.0
HTTP_LONG_TIMEOUT = 30.0
HTTP_EXTRA_LONG_TIMEOUT = 60.0
OLLAMA_TIMEOUT = 600.0
WHISPER_TIMEOUT = 30
TTS_TIMEOUT = 15
DB_CONNECTION_TIMEOUT = 15.0
BRAINSTORM_TIMEOUT = 200

# ── Chat ────────────────────────────────────────────────────────────────────
CHAT_HISTORY_LIMIT = 50
CHAT_GIT_TIMEOUT = 10
CHAT_EMERGENCY_SEARCH_LIMIT = 5
CHAT_BRAINSTORM_HISTORY_LIMIT = 50
CHAT_BRAINSTORM_HELPERS_LIMIT = 8

# ── Gatekeeper / Security ──────────────────────────────────────────────────
GATEKEEPER_EVENT_TIMEOUT = 300
CAPABILITY_TTL_MIN = 5

# ── Crawler ─────────────────────────────────────────────────────────────────
CRAWL_SIMPLE_TIMEOUT = 15
CRAWL_SMART_TIMEOUT = 20
CRAWL_DATA_TIMEOUT = 20

# ── Sandbox ─────────────────────────────────────────────────────────────────
SANDBOX_TIMEOUT_DEFAULT = 15
SANDBOX_TIMEOUT_EXEC = 30
SANDBOX_TIMEOUT_BROWSER = 30

# ── LLM Router ──────────────────────────────────────────────────────────────
ROUTER_LOCAL_TIMEOUT = 30
ROUTER_REMOTE_TIMEOUT = 60
ROUTER_SLEEP_BASE = 1.5
ROUTER_MAX_ATTEMPTS = 3

# ── Nudge ───────────────────────────────────────────────────────────────────
NUDGE_TIMEOUT = 1

# ── API ────────────────────────────────────────────────────────────────────
LLM_MODELS_SHORT_TIMEOUT = 0.5
LLM_MODELS_MEDIUM_TIMEOUT = 5.0
LLM_MODELS_LONG_TIMEOUT = 10.0
ADMIN_SYSTEM_PKILL_TIMEOUT = 5
WORKSPACE_SANDBOX_TIMEOUT = 15
PULSE_SLEEP_INTERVAL = 7200
AGENT_STATUS_SLEEP = 1.0
SYSTEM_INFO_SLEEP = 1.0
ADMIN_TOOLS_SLEEP = 3

# ── Brainstorm ──────────────────────────────────────────────────────────────
BRAINSTORM_THREAD_SLEEP = 1.5

# ── Token Economy ──────────────────────────────────────────────────────────
TOKEN_MIDDLEWARE_SLEEP = 0.01

# ── Evolution ──────────────────────────────────────────────────────────────
EVOLUTION_CHAT_HISTORY_LIMIT = 40

# ── Prompt Version Manager ─────────────────────────────────────────────────
PVM_DEFAULT_LIMIT = 10
COMPILER_CHAT_CLEANUP_LIMIT = 1000
