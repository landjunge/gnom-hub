"""Tests for the Presets refactor.

Verifies that:
- The header no longer contains a "Presets" button (moved into Tuning).
- `presets_management.js` has been deleted.
- No remaining references to the old `showPresetsManagement` symbols.
- The Tuning panel has a "Presets" tab with two sub-tabs:
  Agent-Konfiguration + Snapshots.
- `tuningRender_agentConfig` is defined and renders the system + worker groups.
- `tuningRender_snapshots` still works (replaces the old `tuningRender_presets`
  save/load snapshot UI but is registered under `tuningRender_presets` as the
  wrapper that delegates to it).
- The `modal-presets-management` block has been removed; the unrelated
  `modal-save-preset` block (used by the worker sidebar) stays intact.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INDEX = REPO / "src" / "gnom_hub" / "frontend" / "index.html"
DASHBOARD = REPO / "src" / "gnom_hub" / "frontend" / "dashboard.js"
PRESETS_MGMT_JS = REPO / "src" / "gnom_hub" / "frontend" / "presets_management.js"


# ─── File-system sanity ────────────────────────────────────────────────


def test_presets_management_js_deleted():
    """Old per-agent preset editor file must be removed (logic moved into dashboard.js)."""
    assert not PRESETS_MGMT_JS.exists(), (
        f"Expected {PRESETS_MGMT_JS.relative_to(REPO)} to be deleted, "
        "but it still exists."
    )


# ─── index.html ────────────────────────────────────────────────────────


def test_header_has_no_presets_button():
    """The header must no longer expose a 'Presets' button (moved into Tuning)."""
    text = INDEX.read_text(encoding="utf-8")
    # Find the header-right block (button list inside <header>)
    m = re.search(r'<div class="header-right">(.*?)</div>', text, re.S)
    assert m, "Header block 'header-right' not found in index.html"
    header = m.group(1)
    assert ">Presets<" not in header, (
        "Header still contains a 'Presets' button. "
        "It must be removed — the editor now lives inside the Tuning panel."
    )
    # Also confirm no stray onclick to the deleted showPresetsManagement
    assert "showPresetsManagement()" not in header, (
        "Header still references showPresetsManagement()."
    )


def test_modal_presets_management_removed():
    """The standalone modal for the per-agent preset editor must be gone."""
    text = INDEX.read_text(encoding="utf-8")
    assert 'id="modal-presets-management"' not in text, (
        "modal-presets-management must be removed from index.html."
    )
    assert "closePresetsManagement" not in text, (
        "index.html still references closePresetsManagement — modal is gone."
    )


def test_presets_management_script_tag_removed():
    """The <script src='...presets_management.js'> tag must be gone."""
    text = INDEX.read_text(encoding="utf-8")
    assert "presets_management.js" not in text, (
        "index.html still loads presets_management.js — file is deleted, "
        "tag must be removed too."
    )


def test_modal_save_preset_kept_for_worker_sidebar():
    """The unrelated modal-save-preset (used by worker_sidebar.js) must remain."""
    text = INDEX.read_text(encoding="utf-8")
    assert 'id="modal-save-preset"' in text, (
        "modal-save-preset is used by worker_sidebar.js and must stay."
    )


# ─── dashboard.js ──────────────────────────────────────────────────────


def test_dashboard_defines_tuningRender_agentConfig():
    """The moved per-agent editor logic must be reachable under a new global."""
    text = DASHBOARD.read_text(encoding="utf-8")
    assert re.search(
        r"window\.tuningRender_agentConfig\s*=", text
    ), "tuningRender_agentConfig must be defined on window."
    # Must still expose the helper for save/load/create/clone/delete
    for fn in (
        "tuningSaveAgentField",
        "tuningLoadPresetForEdit",
        "tuningCreateNewPreset",
        "tuningCloneCurrentPreset",
        "tuningDeleteCurrentPreset",
        "tuningSwitchPresetsGroup",
    ):
        assert f"window.{fn}" in text, f"{fn} must remain exposed on window."


def test_dashboard_presets_tab_has_two_subtabs():
    """The Tuning 'Presets' tab must host Agent-Konfiguration + Snapshots sub-tabs."""
    text = DASHBOARD.read_text(encoding="utf-8")
    # Tabs definition still references 'presets'
    assert "{id:'presets',   label:'Presets'}" in text, (
        "Tuning tabs must still include the 'presets' tab."
    )
    # Wrapper function exists
    assert "window.tuningRender_presets" in text, (
        "tuningRender_presets wrapper must exist (delegates to sub-tab)."
    )
    # Both sub-tabs are wired up
    assert "tuningSwitchPresetsSub('agent-config')" in text or "tuningSwitchPresetsSub(\\'agent-config\\')" in text
    assert "tuningSwitchPresetsSub('snapshots')" in text or "tuningSwitchPresetsSub(\\'snapshots\\')" in text
    assert "Agent-Konfiguration" in text
    assert "Snapshots" in text
    # Snapshot renderer is the original renamed
    assert "window.tuningRender_snapshots" in text, (
        "tuningRender_snapshots must exist as the inner renderer."
    )


def test_dashboard_no_orphan_preset_management_refs():
    """No code in dashboard.js may still reference the deleted symbols."""
    text = DASHBOARD.read_text(encoding="utf-8")
    for sym in (
        "showPresetsManagement",
        "closePresetsManagement",
        "switchPresetsGroup",
        "loadPresetForEdit",
        "createNewPreset",
        "cloneCurrentPreset",
        "deleteCurrentPreset",
        "saveAgentField",
        "modal-presets-management",
    ):
        assert sym not in text, (
            f"dashboard.js still references deleted symbol '{sym}'."
        )


def test_dashboard_presets_tab_renders_system_and_worker_groups():
    """tuningRender_agentConfig must render both group tabs."""
    text = DASHBOARD.read_text(encoding="utf-8")
    # Extract the function body
    m = re.search(
        r"window\.tuningRender_agentConfig\s*=\s*async function\s*\([^)]*\)\s*\{(.*?)\n\};",
        text,
        re.S,
    )
    assert m, "Could not locate tuningRender_agentConfig body."
    body = m.group(1)
    assert "preset-group-tab" in body, (
        "tuningRender_agentConfig must render the group-tab buttons."
    )
    assert "preset-group-system" in body and "preset-group-worker" in body, (
        "Both System + Worker group tabs must be present in the agent-config tab."
    )
    assert "presets-agents-grid" in body and "presets-list-select" in body, (
        "The preset dropdown and the per-agent editor grid must both render."
    )


def test_dashboard_snapshot_renderer_still_works():
    """tuningRender_snapshots (renamed tuningRender_presets body) keeps save/load."""
    text = DASHBOARD.read_text(encoding="utf-8")
    # The snapshot save / load endpoints stay untouched
    assert "'/presets'" in text
    assert "'/presets/save'" in text
    assert "'/presets/load'" in text
    # The public helpers remain
    assert "window.tuningSavePreset" in text
    assert "window.tuningLoadPreset" in text


def test_layer_a_endpoints_intact():
    """The /api/presets/layer-a/* endpoints (per-agent preset DB) must stay wired up."""
    text = DASHBOARD.read_text(encoding="utf-8")
    for ep in (
        "/presets/layer-a/list",
        "/presets/groups",
        "/presets/layer-a/",
    ):
        assert ep in text, f"Endpoint {ep} must still be reachable from dashboard.js."
