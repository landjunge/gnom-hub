# Gnom-Hub Diagram Sources

This directory holds the Mermaid source files for the architecture diagrams used in:

- [`README.md`](../../README.md) — embedded inline
- [`README.de.md`](../../README.de.md) — embedded inline
- [`db-architecture.html`](../../../gnom-Workspace/default/db-architecture.html) — interactive page

## Files

| File | Diagram | Used in |
|------|---------|---------|
| `01-memory-flow.mmd` | 3-layer memory lookup (HOT → WARM → COLD) | README §🧠 |
| `02-query-sequence.mmd` | User query through 5 databases | README §🏗️ |
| `03-offload-flow.mmd` | Context-offload via Mermaid canvas + node_id | README §🧠 |
| `04-migration-flow.mmd` | Bootstrap migration logic | README §🧪 |

## Palette

The diagrams use a **paper-and-ink** palette inspired by editorial design:

- **Forest green** `#2d5a3d` — primary, HOT state
- **Copper** `#b8743a` — accent, decision points, offload action
- **Slate** `#4a5a6a` — secondary, recall action
- **Gold** `#c9a449` — restore, completion
- **Paper** `#fdfaf2` — node backgrounds (light)

This palette is designed to:
1. Read well on cream/light backgrounds
2. Survive black-and-white printing (each color is also a different shade)
3. Be color-blind safe (varied luminance + 1.5px borders)
4. Render identically in GitHub-flavoured Markdown + Mermaid.live + custom HTML

## Editing

To update a diagram, edit the `.mmd` file here, then either:
- Copy the mermaid block into the README files
- Or reference the file path with `mermaid-cli`: `mmdc -i 01-memory-flow.mmd -o build/01-memory-flow.svg`

## Rendering in different contexts

**GitHub Markdown** (README.md, README.de.md):
```markdown
\`\`\`mermaid
[paste contents of .mmd here]
\`\`\`
```

**Standalone HTML** (db-architecture.html): uses `<script src="mermaid@10">` with `theme: 'base'` + custom `themeVariables`. See HTML source for full theme config.

**PDF / Print**: use `mermaid-cli` (`mmdc`) to render `.mmd` to SVG, then embed in LaTeX/InDesign.
