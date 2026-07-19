#!/bin/bash
# Schneller E2E-Check: Health, Agents, Showbox, HTML-Datei.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
URL="http://127.0.0.1:${GNOM_HUB_PORT:-3002}"
HTML="${HOME}/gnom-Workspace/default/stunning_test.html"
fail=0

echo "=== E2E Delivery Check @ $URL ==="

if ! curl -sf -m 5 "$URL/api/health" >/tmp/gnom_health.json; then
  echo "FAIL health unreachable"
  exit 1
fi
python3 - <<'PY'
import json
h=json.load(open("/tmp/gnom_health.json"))
print("health:", h.get("status"), h.get("agents"))
assert h.get("status") in ("ok","degraded"), h
s=h.get("agents") or {}
assert s.get("healthy",0) >= 4, s  # mindestens 4 agents online
print("PASS health")
PY

curl -sf -m 5 "$URL/api/showbox/active" >/tmp/gnom_active.json
python3 - <<'PY'
import json
a=json.load(open("/tmp/gnom_active.json"))
print("active showbox:", a)
assert a.get("active"), a
print("PASS showbox active")
PY

if [ -f "$HTML" ] && [ -s "$HTML" ]; then
  echo "PASS html file ($HTML, $(wc -c < "$HTML") bytes)"
else
  echo "FAIL html missing: $HTML"
  fail=1
fi

curl -sf -m 5 "$URL/api/agents?health=true" >/tmp/gnom_agents.json || true
python3 - <<'PY'
import json
try:
  d=json.load(open("/tmp/gnom_agents.json"))
except Exception as e:
  print("WARN agents list", e); raise SystemExit(0)
z=[a for a in d if (a.get("effective_status") or a.get("status"))=="zombie"]
print(f"agents={len(d)} zombies={len(z)}")
if z:
  print("WARN zombies:", [a.get("name") for a in z])
else:
  print("PASS no zombies")
PY

if [ "$fail" = "1" ]; then
  echo "=== E2E FAILED ==="
  exit 1
fi
echo "=== E2E PASSED ==="
