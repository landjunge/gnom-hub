#!/usr/bin/env python3
"""
GNOM-HUB MCP SERVER — MCP over SSE
==========================================================
Echter MCP-Server mit SSE-Transport auf Port 3102.
Ermoeglicht Gravid (Antigravity) direkten Zugriff auf den Gnom-Hub Speicher.

Verbinden: Antigravity -> mcp.json -> http://localhost:3102/sse
"""
import json
import os
import sys
import asyncio
import uuid
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import find_free_port

HOST = "127.0.0.1"
PORT = int(os.environ.get("CORTEX_MCP_PORT", find_free_port(3100, 3200)))
SERVER_NAME = "Cortex_Hub_MCP"


class MCPSession:
    def __init__(self, sid):
        self.id = sid
        self.queue = asyncio.Queue()
        self.initialized = False

    async def send(self, data):
        await self.queue.put(data)

    async def send_result(self, req_id, result):
        msg = {"jsonrpc": "2.0", "id": req_id, "result": result}
        await self.send("event: message\ndata: " + json.dumps(msg) + "\n\n")

    async def send_error(self, req_id, code, message):
        msg = {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
        await self.send("event: message\ndata: " + json.dumps(msg) + "\n\n")


sessions = {}


def new_session():
    sid = str(uuid.uuid4())
    sessions[sid] = MCPSession(sid)
    return sessions[sid]


# ── MCP Tool Definitions ──

MCP_TOOLS = []

def run_tool(tool_name, args):
    """Execute a MCP tool call (blocking, runs in executor)."""
    return {"error": f"Unbekanntes Tool: {tool_name}"}


# ═══════════════════════════════════════════
# HTTP Server
# ═══════════════════════════════════════════

def json_response(data, status=200):
    body = json.dumps(data, indent=2, ensure_ascii=False)
    return (
        f"HTTP/1.1 {status} {'OK' if status == 200 else 'Error'}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body.encode())}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"\r\n{body}"
    ).encode()


def cors_headers():
    return "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nAccess-Control-Allow-Headers: *\r\n"


async def full_read(reader, timeout=10):
    """Read full HTTP request (headers + body)."""
    data = b""
    while True:
        chunk = await asyncio.wait_for(reader.read(65536), timeout=timeout)
        if not chunk:
            break
        data += chunk
        # Check if we have complete headers
        if b"\r\n\r\n" in data:
            header_end = data.index(b"\r\n\r\n")
            headers_raw = data[:header_end].decode("utf-8", errors="replace")
            body = data[header_end + 4:]

            # Get Content-Length
            cl = 0
            for line in headers_raw.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    cl = int(line.split(":")[1].strip())

            if not cl or len(body) >= cl:
                break
    return data


def parse_http(data):
    """Parse raw HTTP request."""
    if not data:
        return None, None, None, {}
    decoded = data.decode("utf-8", errors="replace")
    lines = decoded.split("\r\n")
    if not lines:
        return None, None, None, {}
    parts = lines[0].split(" ")
    method = parts[0] if len(parts) > 0 else "GET"
    path = parts[1] if len(parts) > 1 else "/"

    headers = {}
    body_start = decoded.find("\r\n\r\n")
    for line in lines[1:]:
        if line == "" or line == "\r":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    body = decoded[body_start + 4:] if body_start > 0 else ""
    return method, path, headers, body


async def handle_request(reader, writer):
    try:
        data = await full_read(reader)
        if not data:
            writer.close()
            return

        method, path, headers, body = parse_http(data)

        # CORS preflight
        if method == "OPTIONS":
            resp = (f"HTTP/1.1 204 No Content\r\n{cors_headers()}\r\n").encode()
            writer.write(resp)
            await writer.drain()
            writer.close()
            return

        print(f"[MCP] {method} {path}")

        # ── GET /sse: SSE-Stream ──
        if method == "GET" and path == "/sse":
            session = new_session()
            post_url = f"/message?session_id={session.id}"

            # SSE-Header
            hdrs = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/event-stream\r\n"
                "Cache-Control: no-cache\r\n"
                "Connection: keep-alive\r\n"
                f"{cors_headers()}"
                "\r\n"
            )
            writer.write(hdrs.encode())
            # Send endpoint event
            writer.write(f"event: endpoint\ndata: {post_url}\n\n".encode())
            await writer.drain()

            print(f"[MCP] SSE connected: session={session.id}")

            try:
                while True:
                    try:
                        payload = await asyncio.wait_for(session.queue.get(), timeout=60)
                        writer.write(payload.encode() if isinstance(payload, str) else payload)
                        await writer.drain()
                    except asyncio.TimeoutError:
                        writer.write(": ping\n\n".encode())
                        await writer.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass
            finally:
                sessions.pop(session.id, None)
                print(f"[MCP] SSE disconnected: session={session.id}")

        # ── GET /: Server-Info ──
        elif method == "GET" and path == "/":
            info = {
                "server": SERVER_NAME, "version": "2.0",
                "protocol": "MCP over SSE",
                "sse_endpoint": f"http://{HOST}:{PORT}/sse",
                "sessions_active": len(sessions),
                "database": DB_DIR,
                "tools": [t["name"] for t in MCP_TOOLS],
            }
            writer.write(json_response(info))
            await writer.drain()
            writer.close()

        # ── POST /message: JSON-RPC ──
        elif method == "POST" and path.startswith("/message"):
            parsed = urlparse(path)
            qp = {}
            if parsed.query:
                for p in parsed.query.split("&"):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        qp[k] = v
            session_id = qp.get("session_id", "")
            session = sessions.get(session_id)

            if not session:
                writer.write(json_response({"error": "Session not found"}, 404))
                await writer.drain()
                writer.close()
                return

            try:
                rpc = json.loads(body)
            except json.JSONDecodeError:
                writer.write(json_response({"error": "Invalid JSON"}, 400))
                await writer.drain()
                writer.close()
                return

            rpc_id = rpc.get("id")
            rpc_method = rpc.get("method", "")
            params = rpc.get("params", {})

            print(f"[MCP] JSON-RPC: {rpc_method} id={rpc_id}")

            if rpc_method == "initialize":
                ver = params.get("protocolVersion", "2024-11-05")
                session.initialized = True
                await session.send_result(rpc_id, {
                    "protocolVersion": ver,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": "2.0"}
                })

            elif rpc_method == "notifications/initialized":
                pass

            elif rpc_method == "ping":
                await session.send_result(rpc_id, {})

            elif rpc_method == "tools/list":
                await session.send_result(rpc_id, {"tools": MCP_TOOLS})

            elif rpc_method == "tools/call":
                tname = params.get("name", "")
                targs = params.get("arguments", {})
                result = await asyncio.get_event_loop().run_in_executor(
                    None, run_tool, tname, targs)
                await session.send_result(rpc_id, {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]
                })

            elif rpc_method == "resources/list":
                await session.send_result(rpc_id, {"resources": []})

            else:
                await session.send_error(rpc_id, -32601, f"Method not found: {rpc_method}")

            # POST response (results go via SSE)
            writer.write(b"HTTP/1.1 202 Accepted\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            writer.close()

        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            writer.close()

    except Exception as e:
        print(f"[MCP] Error: {e}")
        try:
            writer.close()
        except Exception:
            pass


async def async_main():
    server = await asyncio.start_server(handle_request, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"\n  ╔══════════════════════════════════════════╗")
    print(f"  ║   GNOM-HUB MCP Server                    ║")
    print(f"  ║   http://{addr[0]}:{addr[1]}/sse                ║")
    print(f"  ║   Tools: {len(MCP_TOOLS)} registriert              ║")
    print(f"  ╚══════════════════════════════════════════╝\n")
    async with server:
        await server.serve_forever()

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("[MCP] Server stopped.")

if __name__ == "__main__":
    main()
