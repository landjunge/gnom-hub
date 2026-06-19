# Gnom-Hub Developer Handover Report
**Date:** May 19, 2026
**Target:** Incoming Developer
**Status:** Handover / Stability & Debugging Phase

---

## 1. System Architecture & Recent Stability Fixes

The Gnom-Hub is built with a **FastAPI** backend (`hub_app.py`) serving a vanilla HTML/JS frontend (`index.html`) on port `3002`. The system orchestrates multiple autonomous agents (`GeneralAG`, `SummarizerAG`, etc.) running as separate Python subprocesses that communicate via a local JSON-based pseudo-database (`db.py`).

### 1.1 The "Nuke" Restart Mechanism
**Problem:** The previous restart mechanism (`routes_admin.py` -> `nuke_restart`) used `os.execv` to restart the server. This caused massive process cloning/zombie processes, preventing the new server from binding to port `3002` (leaving it stuck in `TIME_WAIT` or fully occupied).
**Fix Implemented:** 
*   Removed `os.execv`. The child server process now signals the parent wrapper via `os._exit(42)`.
*   The parent process (`__main__.py`) wraps the server execution in a `while True:` loop. If it catches exit code `42`, it cleanly loops and restarts the server process.
*   **Crucial Detail:** `routes_admin.py`'s `kill_process` loop previously included `"gnom_hub"` in its target list, which killed the parent script before it could catch the exit code. This has been removed. The Nuke restart is now 100% stable.

### 1.2 Frontend Port Discovery & Browser Compatibility
**Problem:** Users experienced false-positive "Hub unreachable" errors when opening `index.html` locally.
**Fix Implemented:**
*   The `discoverPort` function previously relied on `AbortSignal.timeout(2000)`. This feature is unsupported in older browsers (e.g., Safari < 16), which threw a `TypeError`, instantly crashing the UI initialization.
*   Replaced with a custom `AbortController` and `setTimeout` logic for full cross-browser compatibility.
*   Wrapped the main `init()` IIFE in `index.html` in a `try...catch` block to print actual Javascript errors to the UI instead of a generic "Hub unreachable" screen.

---

## 2. Current Known Issues (Blockers)

Despite the core stability fixes, the user is experiencing a complete halt in agent responsiveness ("nichts geht") accompanied by "Hub unreachable" toasts when attempting to chat. 

### 2.1 The `422 Unprocessable Entity` Flood
**Symptom:** The backend logs (`logs_hub.txt`) are flooded with the following error multiple times per second:
```
INFO: 127.0.0.1:56770 - "POST /api/agents/GeneralAG/status HTTP/1.1" 422 Unprocessable Entity
```
**Technical Analysis:**
*   **Endpoint:** `routes_agents.py` exposes `@router.api_route("/api/agents/{a_id}/status", methods=["PUT", "POST"])` with the signature `def set_status(a_id: str, status: str):`.
*   **Validation Error:** FastAPI expects `status` as a query parameter (e.g., `?status=online`). If a client sends a `POST` request with JSON body `{"status": "online"}` but omits the query parameter, FastAPI immediately throws a `422 Validation Error`.
*   **Source:** The frontend (`index.html`) correctly uses `PUT ...?status=${next}`. Therefore, the erroneous `POST` request is almost certainly originating from the Python backend itself—likely from an agent's internal loop (`agent_base.py`) utilizing `self.post()`, or a rogue background thread attempting to sync status but formatting the request incorrectly. 

### 2.2 Chat Payload & ZWC (Zero-Width Characters)
**Symptom:** When the user sends a message like `@GeneralAG Teste den smart_crawl...`, the UI may freeze, fail to display the message, or the agent may fail to respond.
**Technical Analysis:**
*   The `brainstorm_helpers.py` contains logic (`strip_zwc`) to handle Zero-Width Characters (steganographic memory) used by the agents.
*   Browser tests revealed that the UI is receiving massive payloads of hundreds of thousands of hidden/zero-width Unicode characters. 
*   **Hypothesis:** The frontend `fetch` to `/api/chat` might be failing or timing out due to payload size, causing the `api()` wrapper in `index.html` to return `null`. When `sendMessage()` receives `null`, it incorrectly triggers the fallback toast: `toast('Hub unreachable', 'error')`. This leads the user to believe the server is offline, when in reality, the chat endpoint just choked on the massive string.

---

## 3. Next Steps for the Developer

To achieve a fully operational state, the following steps must be executed:

1.  **Trace the 422 Error:** 
    *   Search the entire repository (including all agent scripts in the root directory and `src/gnom_hub/`) for any script hitting the `/status` endpoint via `requests.post` or `self.post`.
    *   **Fix:** Ensure the status is passed as a query parameter (`params={"status": "..."}`) rather than a JSON body, OR update the FastAPI route in `routes_agents.py` to accept a Pydantic model for the request body.
2.  **Fix the Chat UI Fallback:**
    *   In `index.html`, inside `sendMessage()`, change `} else { toast('Hub unreachable', 'error'); }` to display the actual network/HTTP error so the user isn't misled into thinking the server crashed.
3.  **Investigate ZWC Bloat:**
    *   Check the `memory.json` database. If agents are injecting exponential amounts of ZWC data into their responses, the JSON file will bloat, causing `loadAgents()` and `loadChat()` to become unacceptably slow or crash the browser tab. Implement a hard limit on ZWC string length before writing to the DB.
4.  **Consolidate Agent Files:**
    *   Ensure all agent execution files (`generalAG.py`, `summarizerAG.py`, etc.) are correctly located and imported. There appears to be duplication or execution confusion between the root directory and `src/gnom_hub/`.
