#!/usr/bin/env python3
"""Erzeugt 3 Schema-Diagramme der Gnom-Hub Agenten-Kommunikation."""
import matplotlib

matplotlib.use("Agg")
import os

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = "docs/schemas"
os.makedirs(OUT, exist_ok=True)

AGENTS = [
    ("BrainAG",  "Denker / Planer"),
    ("CoderAG",  "Code-Werkstatt"),
    ("SearchAG", "Suche / Web"),
    ("MediaAG",  "Video / TTS"),
    ("ShowboxAG","Slides / Showbox"),
    ("WorkAG",   "Workflows"),
    ("SoulAG",   "Bewusstsein / Lernen"),
    ("GeneralAG","Allrounder"),
]

AGENT_COLORS = {
    "BrainAG":   "#FFD6D6",
    "CoderAG":   "#D6E5FF",
    "SearchAG":  "#D6FFE5",
    "MediaAG":   "#FFE5D6",
    "ShowboxAG": "#E5D6FF",
    "WorkAG":    "#FFFAD6",
    "SoulAG":    "#FFD6F0",
    "GeneralAG": "#D6FFFF",
}


def box(ax, x, y, w, h, label, sub=None, color="#FFFFFF", fontsize=9, weight="bold"):
    p = FancyBboxPatch((x - w/2, y - h/2), w, h,
                       boxstyle="round,pad=0.02,rounding_size=0.08",
                       linewidth=1.2, edgecolor="#333333", facecolor=color)
    ax.add_patch(p)
    ax.text(x, y + (0.07 if sub else 0), label, ha="center", va="center",
            fontsize=fontsize, fontweight=weight)
    if sub:
        ax.text(x, y - 0.13, sub, ha="center", va="center",
                fontsize=fontsize - 1.5, color="#555555", style="italic")


def arrow(ax, x1, y1, x2, y2, label=None, color="#666666", style="-|>",
          rad=0.0, lw=1.4, fontsize=8):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle=style, mutation_scale=14,
                        color=color, linewidth=lw,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my + 0.05, label, ha="center", va="center",
                fontsize=fontsize, color=color,
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                          edgecolor="none", alpha=0.85))


# ============================================================
# BILD 1: High-Level  (8 Agenten + 4 Haupt-DBs + Hauptflüsse)
# ============================================================
fig, ax = plt.subplots(figsize=(16, 11))
ax.set_xlim(0, 16); ax.set_ylim(0, 11)
ax.axis("off")
ax.set_title("Gnom-Hub: Agenten-Kommunikation — High-Level",
             fontsize=15, fontweight="bold", pad=12)

# 8 Agenten im Kreis um den Hub (Mitte)
import math

cx, cy, R = 8.0, 5.5, 2.6
agent_pos = {}
for i, (name, sub) in enumerate(AGENTS):
    a = math.radians(90 - i * 45)
    x, y = cx + R * math.cos(a), cy + R * math.sin(a)
    agent_pos[name] = (x, y)
    box(ax, x, y, 1.9, 0.95, name, sub, color=AGENT_COLORS[name])

# Linien Agent → Hub (Bus-Topologie)
for name, (x, y) in agent_pos.items():
    arrow(ax, x, y, cx, cy, color="#999999", lw=0.7)

# Hub in der Mitte (schwarzer Kasten mit weißem Text)
hub_w, hub_h = 1.6, 0.85
p = FancyBboxPatch((cx - hub_w/2, cy - hub_h/2), hub_w, hub_h,
                   boxstyle="round,pad=0.02,rounding_size=0.1",
                   linewidth=1.5, edgecolor="#000", facecolor="#222")
ax.add_patch(p)
ax.text(cx, cy + 0.12, "Hub", ha="center", va="center",
        color="white", fontsize=11, fontweight="bold")
ax.text(cx, cy - 0.18, "Orchestrator", ha="center", va="center",
        color="#cccccc", fontsize=8, style="italic")

# 4 DBs am Rand (außerhalb des Agenten-Kreises, an den 4 Ecken)
# Positionen sind außerhalb des Agenten-Kreises (Radius 2.6)
DBs = [
    ("gnomhub.db",        "Haupt-DB · 14 Tabellen",  1.7, 9.3, "#FFE9B3"),  # oben links
    ("rules.db",          "Regeln / Sicherheit",    14.3, 9.3, "#FFCFB3"),  # oben rechts
    ("passive_archive.db","Langzeit-Archiv",         1.7, 1.7, "#B3D9FF"),  # unten links
    ("soul_embeddings",   "FAISS · SoulAG-Memory",  14.3, 1.7, "#FFB3E0"),  # unten rechts
]
for name, sub, x, y, c in DBs:
    box(ax, x, y, 2.9, 0.95, name, sub, color=c, fontsize=9.5)

# Pfeile Hub → DBs: vom Hub-Rand direkt zu den DBs, mit Kurve
# Oben-links
arrow(ax, cx - 0.6, cy + 0.4, 3.0, 9.3, color="#0066cc", lw=1.8,
      label="R/W", rad=0.25)
# Oben-rechts
arrow(ax, cx + 0.6, cy + 0.4, 13.0, 9.3, color="#0066cc", lw=1.8,
      label="R/W", rad=-0.25)
# Unten-links
arrow(ax, cx - 0.6, cy - 0.4, 3.0, 1.7, color="#0066cc", lw=1.8,
      label="R/W", rad=-0.25)
# Unten-rechts
arrow(ax, cx + 0.6, cy - 0.4, 13.0, 1.7, color="#0066cc", lw=1.8,
      label="R/W", rad=0.25)

# Hinweis-Text oben
ax.text(0.3, 10.4, "Bus-Topologie: alle Agenten melden beim Hub. "
        "Der Hub ist Single-Writer für die DBs — Ausnahme: SoulAG schreibt "
        "direkt in soul_memory.",
        fontsize=9.5, color="#333")

# Legende unten
ax.text(0.3, 0.2,
        "Graue Pfeile = Agent ↔ Hub (Lese-/Schreib-Aufrufe).  "
        "Blaue Pfeile = Hub ↔ DB (R/W).",
        fontsize=9, color="#333")

plt.tight_layout()
plt.savefig(f"{OUT}/01_highlevel.png", dpi=140, bbox_inches="tight")
plt.close()
print("✓ 01_highlevel.png")


# ============================================================
# BILD 2: Mittel — Tabellen + R/W pro Agent
# ============================================================
fig, ax = plt.subplots(figsize=(18, 12))
ax.set_xlim(0, 18); ax.set_ylim(0, 12)
ax.axis("off")
ax.set_title("Gnom-Hub: Agenten ↔ Tabellen (R/W)",
             fontsize=15, fontweight="bold", pad=12)

# 8 Agenten links
for i, (name, sub) in enumerate(AGENTS):
    y = 11 - i * 1.35
    box(ax, 2.0, y, 2.6, 0.95, name, sub, color=AGENT_COLORS[name])

# Tabellen rechts (gruppiert nach DB)
TABLES = [
    # (db, tab, y, color)
    ("gnomhub.db", "agents",            11.0,  "#FFE9B3"),
    ("gnomhub.db", "chat",              10.2,  "#FFE9B3"),
    ("gnomhub.db", "agent_messages",     9.4,  "#FFE9B3"),
    ("gnomhub.db", "swarm_callbacks",    8.6,  "#FFE9B3"),
    ("gnomhub.db", "workflows",          7.8,  "#FFE9B3"),
    ("gnomhub.db", "workflow_tasks",     7.0,  "#FFE9B3"),
    ("gnomhub.db", "audit_log",          6.2,  "#FFE9B3"),
    ("gnomhub.db", "token_budget_*",     5.4,  "#FFE9B3"),
    ("rules.db",   "blockade_log",       4.6,  "#FFCFB3"),
    ("rules.db",   "capabilities",       3.8,  "#FFCFB3"),
    ("rules.db",   "agent_capabilities", 3.0,  "#FFCFB3"),
    ("gnomhub.db", "showbox_*",          2.2,  "#FFE9B3"),
    ("gnomhub.db", "soul_memory ★",      1.4,  "#FFB3E0"),
    ("archive",    "explainable_*",      0.6,  "#B3D9FF"),
]

for db, tab, y, c in TABLES:
    x = 10.0
    box(ax, x, y, 3.2, 0.75, tab, db, color=c, fontsize=8.5)
    # DB-Label rechts
    ax.text(13.0, y, "●", ha="center", va="center", fontsize=10,
            color={"gnomhub.db":"#C68F00","rules.db":"#C65400",
                   "archive":"#0066AA"}.get(db, "#555"))

# R/W-Zuordnungen (welcher Agent liest/schreibt was)
# Format: (agent, table_label, access)  access ∈ {"R","W","RW"}
ACCESS = [
    # jeder Agent liest/schreibt eigene Zeile in agents
    ("BrainAG",  "agents", "RW"),
    ("CoderAG",  "agents", "RW"),
    ("SearchAG", "agents", "RW"),
    ("MediaAG",  "agents", "RW"),
    ("ShowboxAG","agents", "RW"),
    ("WorkAG",   "agents", "RW"),
    ("SoulAG",   "agents", "R"),
    ("GeneralAG","agents", "RW"),
    # chat — alle schreiben
    ("BrainAG",  "chat", "W"), ("CoderAG", "chat", "W"),
    ("SearchAG", "chat", "W"), ("MediaAG", "chat", "W"),
    ("ShowboxAG","chat", "W"), ("WorkAG", "chat", "W"),
    ("SoulAG",   "chat", "R"), ("GeneralAG","chat", "W"),
    # agent_messages
    ("BrainAG",  "agent_messages", "W"), ("WorkAG",  "agent_messages", "W"),
    ("SoulAG",   "agent_messages", "R"),
    # swarm_callbacks
    ("WorkAG",   "swarm_callbacks", "W"), ("SoulAG",  "swarm_callbacks", "R"),
    # workflows
    ("WorkAG",   "workflows", "RW"), ("BrainAG", "workflows", "R"),
    # audit_log
    ("SoulAG",   "audit_log", "R"), ("BrainAG", "audit_log", "R"),
    # blockade_log — alle Agenten
    ("BrainAG",  "blockade_log", "W"), ("CoderAG",  "blockade_log", "W"),
    ("SearchAG", "blockade_log", "W"), ("MediaAG",  "blockade_log", "W"),
    ("ShowboxAG","blockade_log", "W"), ("WorkAG",   "blockade_log", "W"),
    ("SoulAG",   "blockade_log", "R"), ("GeneralAG","blockade_log", "W"),
    # capabilities / agent_capabilities — via Security-Layer
    ("BrainAG",  "capabilities", "R"), ("CoderAG",  "capabilities", "R"),
    ("SearchAG", "capabilities", "R"), ("MediaAG",  "capabilities", "R"),
    ("ShowboxAG","capabilities", "R"), ("WorkAG",   "capabilities", "R"),
    ("SoulAG",   "capabilities", "R"), ("GeneralAG","capabilities", "R"),
    # token_budget_*
    ("BrainAG",  "token_budget_*", "W"), ("CoderAG","token_budget_*", "W"),
    ("SearchAG", "token_budget_*", "W"), ("MediaAG","token_budget_*", "W"),
    ("ShowboxAG","token_budget_*", "W"), ("WorkAG", "token_budget_*", "W"),
    ("SoulAG",   "token_budget_*", "R"), ("GeneralAG","token_budget_*", "W"),
    # showbox_*
    ("ShowboxAG","showbox_*", "RW"), ("BrainAG", "showbox_*", "R"),
    # soul_memory — NUR SoulAG schreibt, alle lesen
    ("SoulAG",   "soul_memory ★", "W"),
    ("BrainAG",  "soul_memory ★", "R"), ("CoderAG",  "soul_memory ★", "R"),
    ("SearchAG", "soul_memory ★", "R"), ("MediaAG",  "soul_memory ★", "R"),
    ("ShowboxAG","soul_memory ★", "R"), ("WorkAG",   "soul_memory ★", "R"),
    ("GeneralAG","soul_memory ★", "R"),
    # explainable_outputs
    ("SoulAG",   "explainable_*", "W"), ("BrainAG", "explainable_*", "R"),
]

AGENT_Y = {n: 11 - i * 1.35 for i, (n, _) in enumerate(AGENTS)}
TAB_Y = {t: y for _, t, y, _ in TABLES}

for ag, tab, acc in ACCESS:
    ay = AGENT_Y[ag]
    if tab not in TAB_Y: continue
    ty = TAB_Y[tab]
    color = {"R":"#1f77b4", "W":"#d62728", "RW":"#2ca02c"}[acc]
    style = "-|>" if acc != "RW" else "<|-|>"
    arrow(ax, 3.3, ay, 8.4, ty, color=color, lw=0.6, style=style, rad=0.0)

# Legende
leg = [
    mpatches.Patch(color="#1f77b4", label="R — Liest"),
    mpatches.Patch(color="#d62728", label="W — Schreibt"),
    mpatches.Patch(color="#2ca02c", label="RW — Liest + Schreibt"),
]
ax.legend(handles=leg, loc="upper right", fontsize=9)

# Hinweis unten
ax.text(0.3, 0.05,
        "★ soul_memory: nur SoulAG schreibt. Quelle als [source:AGENT] im value-Feld.",
        fontsize=9, color="#aa0066", style="italic")

plt.tight_layout()
plt.savefig(f"{OUT}/02_tables_rw.png", dpi=140, bbox_inches="tight")
plt.close()
print("✓ 02_tables_rw.png")


# ============================================================
# BILD 3: Detail — Spalten + Trigger
# ============================================================
fig, ax = plt.subplots(figsize=(20, 14))
ax.set_xlim(0, 20); ax.set_ylim(0, 14)
ax.axis("off")
ax.set_title("Gnom-Hub: Datenbank-Schema (Tabellen + Spalten)",
             fontsize=15, fontweight="bold", pad=12)

# 14 Tabellen in Grid 4 Spalten × ~4 Zeilen
GRID = [
    # (table, db, color, cols)
    ("agents",      "gnomhub.db", "#FFD6D6",
     ["name PK","id","port","description","status",
      "circuit_state","consecutive_failures","last_heartbeat"]),
    ("chat",        "gnomhub.db", "#D6E5FF",
     ["id PK","project","sender","agent_id","msg_type",
      "content","timestamp","token_cost"]),
    ("agent_messages","gnomhub.db", "#D6E5FF",
     ["id PK","sender","recipient","payload",
      "priority","timestamp","delivered"]),
    ("swarm_callbacks","gnomhub.db", "#D6E5FF",
     ["idempotency_key PK","context_id","agent_name",
      "result_json","received_at"]),
    ("workflows",   "gnomhub.db", "#FFFAD6",
     ["id PK","name","status","created_at","completed_at"]),
    ("workflow_tasks","gnomhub.db", "#FFFAD6",
     ["workflow_id FK","task_id","capability",
      "input_template","depends_on","result"]),
    ("audit_log",   "gnomhub.db", "#FFE5D6",
     ["id PK","timestamp","agent","event_type","details"]),
    ("token_budget_logs","gnomhub.db", "#FFE5D6",
     ["operation_id","agent","operation_type",
      "input_tokens","output_tokens","timestamp"]),
    ("token_budget_alerts","gnomhub.db", "#FFE5D6",
     ["id PK","message","timestamp","acknowledged"]),
    ("showbox_presentations","gnomhub.db", "#E5D6FF",
     ["id PK","name","slides","sender","updated_at"]),
    ("soul_memory ★","gnomhub.db", "#FFD6F0",
     ["id PK","key","value","timestamp","priority","source"]),
    ("explainable_outputs","passive_archive.db", "#B3D9FF",
     ["id PK","agent","task","data","timestamp"]),
    ("capabilities", "rules.db",  "#FFCFB3",
     ["id PK","agent_name","capability_type","resource","granted_by"]),
    ("agent_capabilities","rules.db", "#FFCFB3",
     ["agent_name PK","capability PK","confidence"]),
]

COLS, ROWS = 4, 4
CW, CH = 4.5, 2.6
for idx, (name, db, color, cols) in enumerate(GRID):
    r, c = divmod(idx, COLS)
    x = 1.5 + c * 4.7
    y = 13.3 - r * 3.2
    # Tabelle-Box
    p = FancyBboxPatch((x - CW/2, y - CH/2), CW, CH,
                       boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.0, edgecolor="#333", facecolor=color)
    ax.add_patch(p)
    ax.text(x, y + CH/2 - 0.22, name, ha="center", va="top",
            fontsize=10, fontweight="bold")
    ax.text(x, y + CH/2 - 0.45, db, ha="center", va="top",
            fontsize=7, color="#555", style="italic")
    # Spalten
    for j, col in enumerate(cols):
        ay = y + CH/2 - 0.75 - j * 0.22
        ax.text(x - CW/2 + 0.15, ay, "• " + col, ha="left", va="top",
                fontsize=7.5, family="monospace")

# FK-Pfeile (vereinfacht)
def fk_arrow(x1, y1, x2, y2, label):
    arrow(ax, x1, y1, x2, y2, color="#aa00aa", lw=1.0,
          style="-|>", rad=0.0, label=label, fontsize=7)

# workflows → workflow_tasks
fk_arrow(2.0, 11.0, 7.0, 9.4, "FK")

# FK-Legende
ax.text(0.3, 0.1,
        "★ soul_memory = Single-Writer (SoulAG). "
        "FK-Pfeile zeigen 1:n-Beziehungen. "
        "DB-Dateien: gnomhub.db + rules.db + passive_archive.db (je eigene .db-Datei).",
        fontsize=9, color="#333")

plt.tight_layout()
plt.savefig(f"{OUT}/03_detail_erd.png", dpi=140, bbox_inches="tight")
plt.close()
print("✓ 03_detail_erd.png")
