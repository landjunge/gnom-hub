"""TKG Curator Demo — Phase 1: Text → TKG via CuratorAgent.

Zeigt wie der Curator Texte in Entities, Facts, Relations umwandelt
und bitemporal Konflikte erkennt.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gnom_hub.memory_tkg.curator_agent import CuratorAgent
from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
from gnom_hub.memory_tkg.models import Entity


def main():
    print("🧠 TKG Phase 1 — Curator Demo")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp(prefix="tkg_curator_")
    db_path = f"{tmpdir}/brain.kuzu"
    db = KuzuDBBackend(db_path)

    # Seed-Entities (für die Demo: vordefinierte Domain-Entities)
    print("\n📦 Seeding initial domain entities...")
    for e in [
        Entity(id="e_gpt4", name="GPT-4", type="model", importance=0.9),
        Entity(id="e_claude", name="Claude", type="model", importance=0.9),
        Entity(id="e_kuzu", name="KuzuDB", type="tool", importance=0.95),
        Entity(id="e_faiss", name="FAISS", type="tool", importance=0.7),
    ]:
        db.upsert_entity(e)
    print("   ✓ 4 domain entities seeded")

    # Curator initialisieren
    curator = CuratorAgent(db)
    print(f"\n🤖 Curator ready (backend: {type(db).__name__})")

    # ── Demo 1: User-Message kuratieren ──
    print("\n" + "=" * 60)
    print("📝 Demo 1: User-Message 'Wir nutzen jetzt Claude statt GPT-4'")
    print("=" * 60)
    text1 = "Wir nutzen jetzt Claude statt GPT-4, läuft besser mit KuzuDB."
    report1 = curator.curate(text1, source="user")
    print(f"   Entities extrahiert: {len(report1.entities_extracted)}")
    for e in report1.entities_extracted:
        print(f"     - {e.name} ({e.type}, imp={e.importance:.2f})")
    print(f"   Facts erstellt: {len(report1.facts_created)}")
    print(f"   Relations erstellt: {len(report1.relations_created)}")
    print(f"   Mentions erstellt: {len(report1.mentions_created)}")

    # ── Demo 2: Second Message — temporal conflict ──
    print("\n" + "=" * 60)
    print("📝 Demo 2: User-Message 'FAISS wurde ersetzt durch KuzuDB'")
    print("=" * 60)
    text2 = "FAISS wurde ersetzt durch KuzuDB in der neuen Pipeline."
    report2 = curator.curate(text2, source="user")
    print(f"   Entities extrahiert: {len(report2.entities_extracted)}")
    for e in report2.entities_extracted:
        print(f"     - {e.name} ({e.type}, imp={e.importance:.2f})")
    print(f"   Facts erstellt: {len(report2.facts_created)}")
    print(f"   Facts WIDERRUFEN: {len(report2.facts_invalidated)}")
    for f in report2.facts_invalidated:
        print(f"     ❌ {f.id}: {f.text[:80]}...")

    # ── Demo 3: Agent-Output kuratieren ──
    print("\n" + "=" * 60)
    print("📝 Demo 3: Agent-Output 'KuzuDB fixte die FAISS-ABI-Probleme'")
    print("=" * 60)
    text3 = "KuzuDB fixte die FAISS-ABI-Probleme. TKG nutzt jetzt KuzuDB als Backend."
    report3 = curator.curate(text3, source="GeneralAG")
    print(f"   Entities extrahiert: {len(report3.entities_extracted)}")
    for e in report3.entities_extracted:
        print(f"     - {e.name} ({e.type}, imp={e.importance:.2f})")
    print(f"   Facts erstellt: {len(report3.facts_created)}")
    print(f"   Facts WIDERRUFEN: {len(report3.facts_invalidated)}")

    # ── End-Stats ──
    print("\n" + "=" * 60)
    print("📊 End-Stats:")
    print("=" * 60)
    print(f"   Curator Stats: {curator.stats()}")
    print(f"   Total Entities in TKG: {len(db.find_entities_by_name('')) + len(db.find_entities_by_name('KuzuDB'))} (rough)")
    # Better: get all
    all_entities = []
    for name in ['KuzuDB', 'FAISS', 'GPT-4', 'Claude', 'generalag', 'kuzu', 'claude', 'faiss']:
        all_entities.extend(db.find_entities_by_name(name))
    print(f"   Unique entities: {len(set(e.id for e in all_entities))}")

    # ── HTML-Render ──
    print("\n📊 Rendering Curator-Demo HTML...")
    output_path = "/Users/landjunge/gnom-Workspace/default/tkg_curator_demo.html"
    render_html(db, curator, output_path, [report1, report2, report3])
    print(f"✓ HTML written: {output_path}")

    db.close()
    return output_path


def render_html(db, curator, output_path, reports):
    """Rendert HTML mit allen Reports + finalem TKG-State."""
    # Collect all entities from DB
    all_entities = []
    for name_query in ['GPT-4', 'Claude', 'KuzuDB', 'FAISS', 'generalag', 'kuzu']:
        all_entities.extend(db.find_entities_by_name(name_query))

    mermaid = ["graph TD"]
    for e in all_entities:
        color = {
            "model": "#c9b1ff",
            "tool": "#4ecdc4",
            "agent": "#95e1d3",
            "code_id": "#ffd93d",
            "bug": "#ff6b6b",
        }.get(e.type, "#999")
        mermaid.append(f'    {e.id}["{e.name}<br/><sub>{e.type} · imp={e.importance:.2f}</sub>"]')
        mermaid.append(f'    style {e.id} fill:{color},stroke:#333,stroke-width:2px')

    mermaid.append("    subgraph FACTS")
    for r in reports:
        for f in r.facts_created:
            preview = f.text[:60] + "..." if len(f.text) > 60 else f.text
            mermaid.append(f'        {f.id}[/"{preview}"/]')
    mermaid.append("    end")

    for r in reports:
        for rel in r.relations_created:
            mermaid.append(f'    {rel.from_id} -->|{rel.predicate}| {rel.to_id}')

    mermaid_code = "\n".join(mermaid)

    # Reports HTML
    reports_html = ""
    for i, r in enumerate(reports, 1):
        entities_li = "\n".join(
            f'<li><b>{e.name}</b> <code>{e.type}</code> · importance {e.importance:.2f}</li>'
            for e in r.entities_extracted
        )
        facts_li = "\n".join(f'<li><code>{f.id}</code>: {f.text[:120]}...</li>' for f in r.facts_created)
        invalid_li = "\n".join(
            f'<li class="invalid"><b>❌ INVALIDATED</b> <code>{f.id}</code>: {f.text[:80]}...</li>'
            for f in r.facts_invalidated
        )
        errors_li = "\n".join(f'<li class="error">⚠️ {e}</li>' for e in r.errors)

        reports_html += f"""
        <div class="report">
          <h3>📝 Demo {i}: <code>{r.text[:80]}...</code></h3>
          <div class="metrics">
            <div class="metric"><div class="num">{len(r.entities_extracted)}</div><div class="label">Entities</div></div>
            <div class="metric"><div class="num">{len(r.facts_created)}</div><div class="label">Facts created</div></div>
            <div class="metric"><div class="num">{len(r.facts_invalidated)}</div><div class="label">Facts invalidated</div></div>
            <div class="metric"><div class="num">{len(r.relations_created)}</div><div class="label">Relations</div></div>
          </div>
          {f'<h4>Extracted Entities</h4><ul>{entities_li}</ul>' if entities_li else ''}
          {f'<h4>Created Facts</h4><ul>{facts_li}</ul>' if facts_li else ''}
          {f'<h4>⚠️ Invalidated Facts (Bitemporal!)</h4><ul>{invalid_li}</ul>' if invalid_li else ''}
          {f'<h4>Errors</h4><ul>{errors_li}</ul>' if errors_li else ''}
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>TKG Curator Demo — Phase 1</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #0e0f13; color: #e7e9ee; margin: 0; padding: 24px; }}
  h1 {{ color: #00e5ff; }}
  h2 {{ color: #00e5ff; border-bottom: 1px solid #2a2c33; padding-bottom: 4px; margin-top: 32px; }}
  h3 {{ color: #ffd93d; }}
  h4 {{ color: #95e1d3; margin-bottom: 6px; }}
  .subtitle {{ color: #888; margin-bottom: 24px; }}
  .mermaid {{ background: #1a1c22; padding: 20px; border-radius: 8px; margin: 20px 0; }}
  .report {{ background: #1a1c22; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #00e5ff; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; margin: 12px 0; }}
  .metric {{ background: #0e0f13; padding: 10px 14px; border-radius: 6px; text-align: center; }}
  .metric .num {{ font-size: 1.6em; font-weight: 700; color: #00e5ff; }}
  .metric .label {{ color: #888; font-size: 0.8em; }}
  ul {{ list-style: none; padding-left: 0; }}
  li {{ padding: 6px 10px; margin: 3px 0; background: #0e0f13; border-radius: 4px; border-left: 2px solid #00e5ff; font-size: 0.9em; }}
  li.invalid {{ border-left-color: #ff6b6b; color: #ff6b6b; }}
  li.error {{ border-left-color: #ffd93d; color: #ffd93d; }}
  code {{ background: #2a2c33; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>🧠 TKG Curator Demo — Phase 1</h1>
<p class="subtitle">Text → TKG via CuratorAgent. Heuristik-basierte Entity-Extraktion + bitemporale Konflikterkennung.</p>

<h2>📊 Final TKG-Graph (nach 3 Demos)</h2>
<div class="mermaid">
{mermaid_code}
</div>

<h2>🔄 Curator-Reports</h2>
{reports_html}

<p class="subtitle" style="margin-top:40px">Generiert von <code>scripts/tkg_curator_demo.py</code> — {time.strftime('%Y-%m-%d %H:%M:%S')}</p>

<script>mermaid.initialize({{startOnLoad: true, theme: 'dark', themeVariables: {{primaryColor: '#1a1c22', primaryTextColor: '#e7e9ee', primaryBorderColor: '#00e5ff', lineColor: '#5b8def', fontSize: '14px'}}}});</script>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
