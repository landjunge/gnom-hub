// presets_management.js — Per-Agent Preset Management UI
// Lädt Presets via /api/presets, gruppiert nach System + Worker, per-Agent-Edit-Form.
(function() {
  let _presetsData = null; // Cache: {slugs: [...], currentPreset: {...}, groups: {system, worker}, activeGroup: 'system'}
  let _agentGroups = {system: ['soulag','watchdogag','generalag','securityag'], worker: ['coderag','researcherag','writerag','editorag']};

  const AGENT_LABELS = {
    soulag: 'SoulAG — Identitäts-Anker',
    watchdogag: 'WatchdogAG — Sicherheits-Wächter',
    generalag: 'GeneralAG — Allround-Router',
    securityag: 'SecurityAG — Security-Auditor',
    coderag: 'CoderAG — Code-Worker',
    researcherag: 'ResearcherAG — Recherche-Worker',
    writerag: 'WriterAG — Text-Worker',
    editorag: 'EditorAG — QA-Worker'
  };

  const AGENT_FIELDS = [
    {key: 'prompt', label: 'System-Prompt', type: 'textarea', rows: 6},
    {key: 'focus', label: 'Fokus', type: 'text'},
    {key: 'target', label: 'Target (z.B. auto:stage_2 oder openrouter:modell)', type: 'text'},
    {key: 'creativity', label: 'Creativity (1-5)', type: 'number', min: 1, max: 5},
    {key: 'obedience', label: 'Obedience (1-5)', type: 'number', min: 1, max: 5},
    {key: 'model_override', label: 'Model-Override (oder leer)', type: 'text'},
    {key: 'enabled', label: 'Aktiv', type: 'checkbox'}
  ];

  window.showPresetsManagement = async function() {
    document.getElementById('modal-presets-management').style.display = 'flex';
    await loadPresetsData();
    renderPresetsList();
    renderAgentsGrid();
  };

  window.closePresetsManagement = function() {
    document.getElementById('modal-presets-management').style.display = 'none';
  };

  window.switchPresetsGroup = function(group) {
    _presetsData.activeGroup = group;
    document.querySelectorAll('.preset-group-tab').forEach(b => {
      b.dataset.group === group
        ? (b.style.background = 'rgba(0, 229, 255, 0.18)', b.style.color = 'var(--primary)', b.style.borderColor = 'var(--primary)')
        : (b.style.background = 'rgba(255,255,255,0.04)', b.style.color = 'var(--text-dim)', b.style.borderColor = 'rgba(255,255,255,0.08)');
    });
    renderAgentsGrid();
  };

  window.loadPresetForEdit = function(slug) {
    if (!slug) {
      _presetsData.currentPreset = null;
      renderAgentsGrid();
      return;
    }
    const p = _presetsData.slugs.find(x => x.slug === slug);
    if (!p) return;
    _presetsData.currentPreset = p;
    renderAgentsGrid();
  };

  window.createNewPreset = async function() {
    const name = prompt('Name des neuen Presets:');
    if (!name) return;
    try {
      const r = await fetch('/api/presets/layer-a', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, description: ''})
      });
      if (!r.ok) throw new Error(await r.text());
      await loadPresetsData();
      renderPresetsList();
      const j = await r.json();
      loadPresetForEdit(j.slug);
    } catch (e) {
      alert('Fehler beim Anlegen: ' + e.message);
    }
  };

  window.cloneCurrentPreset = async function() {
    if (!_presetsData.currentPreset) return alert('Bitte erst Preset wählen');
    const name = prompt('Name für den Klon:', _presetsData.currentPreset.name + ' (Kopie)');
    if (!name) return;
    try {
      const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(_presetsData.currentPreset.slug) + '/clone', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
      });
      if (!r.ok) throw new Error(await r.text());
      await loadPresetsData();
      renderPresetsList();
    } catch (e) {
      alert('Fehler beim Klonen: ' + e.message);
    }
  };

  window.deleteCurrentPreset = async function() {
    if (!_presetsData.currentPreset) return alert('Bitte erst Preset wählen');
    if (_presetsData.currentPreset.slug === 'default') return alert('"default" Preset kann nicht gelöscht werden');
    if (!confirm('Preset "' + _presetsData.currentPreset.name + '" wirklich löschen?')) return;
    try {
      const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(_presetsData.currentPreset.slug), {method: 'DELETE'});
      if (!r.ok) throw new Error(await r.text());
      _presetsData.currentPreset = null;
      await loadPresetsData();
      renderPresetsList();
      renderAgentsGrid();
    } catch (e) {
      alert('Fehler beim Löschen: ' + e.message);
    }
  };

  window.saveAgentField = async function(slug, agentName, fieldKey, value) {
    try {
      const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(slug) + '/agents/' + encodeURIComponent(agentName), {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({[fieldKey]: value})
      });
      if (!r.ok) throw new Error(await r.text());
      // Update local cache
      if (_presetsData.currentPreset && _presetsData.currentPreset.agents[agentName]) {
        _presetsData.currentPreset.agents[agentName][fieldKey] = value;
      }
      // Visual feedback
      const el = document.querySelector(`[data-agent="${agentName}"][data-field="${fieldKey}"] .save-status`);
      if (el) { el.textContent = '✓ gespeichert'; el.style.color = '#4ade80'; setTimeout(() => { el.textContent = ''; }, 2000); }
    } catch (e) {
      alert('Fehler beim Speichern: ' + e.message);
    }
  };

  async function loadPresetsData() {
    try {
      const [presetsRes, groupsRes] = await Promise.all([
        fetch('/api/presets/layer-a/list').then(r => r.json()),
        fetch('/api/presets/groups').then(r => r.json()).catch(() => null)
      ]);
      if (groupsRes) _agentGroups = groupsRes;
      _presetsData = {
        slugs: presetsRes || [],
        currentPreset: null,
        activeGroup: 'system'
      };
      // Auto-select first preset
      if (_presetsData.slugs.length > 0) {
        try {
          const r = await fetch('/api/presets/layer-a/' + encodeURIComponent(_presetsData.slugs[0].slug));
          _presetsData.currentPreset = await r.json();
        } catch (e) { /* ignore */ }
      }
    } catch (e) {
      console.error('loadPresetsData failed:', e);
    }
  }

  function renderPresetsList() {
    const sel = document.getElementById('presets-list-select');
    if (!sel) return;
    sel.innerHTML = '';
    if (!_presetsData || !_presetsData.slugs.length) {
      sel.innerHTML = '<option value="">— keine Presets —</option>';
      return;
    }
    _presetsData.slugs.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.slug;
      opt.textContent = p.name + ' (' + p.agent_count + ' Agents)';
      if (_presetsData.currentPreset && _presetsData.currentPreset.slug === p.slug) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  function renderAgentsGrid() {
    const grid = document.getElementById('presets-agents-grid');
    if (!grid) return;
    if (!_presetsData) { grid.innerHTML = '<p style="color: var(--text-dim);">Lade Presets…</p>'; return; }
    const group = _presetsData.activeGroup || 'system';
    const agents = _agentGroups[group] || [];
    const preset = _presetsData.currentPreset;
    if (!preset) {
      grid.innerHTML = '<p style="color: var(--text-dim); padding: 20px; text-align: center;">Wähle ein Preset zum Bearbeiten</p>';
      return;
    }
    let html = '';
    agents.forEach(agentName => {
      const agentData = (preset.agents && preset.agents[agentName]) || {};
      const label = AGENT_LABELS[agentName] || agentName;
      html += '<div class="preset-agent-card" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 12px;">';
      html += '<h3 style="margin: 0 0 8px 0; font-size: 0.9rem; color: var(--primary); display: flex; justify-content: space-between; align-items: center;">';
      html += '<span>' + label + '</span>';
      html += '<small style="color: var(--text-dim); font-size: 0.65rem;">' + agentName + '</small></h3>';
      AGENT_FIELDS.forEach(f => {
        const val = agentData[f.key];
        html += '<div data-agent="' + agentName + '" data-field="' + f.key + '" style="margin-bottom: 8px;">';
        html += '<label style="display: block; font-size: 0.7rem; color: var(--text-dim); margin-bottom: 2px;">' + f.label + ' <span class="save-status" style="margin-left: 6px; font-size: 0.65rem;"></span></label>';
        if (f.type === 'textarea') {
          html += '<textarea rows="' + (f.rows || 4) + '" data-oninput="saveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.value)" style="width: 100%; padding: 6px; background: var(--bg-input); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; color: var(--text); font-size: 0.75rem; font-family: inherit; resize: vertical;">' + (val || '') + '</textarea>';
        } else if (f.type === 'checkbox') {
          html += '<input type="checkbox" ' + (val ? 'checked' : '') + ' onchange="saveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.checked)" style="width: 18px; height: 18px;">';
        } else if (f.type === 'number') {
          html += '<input type="number" min="' + (f.min || 0) + '" max="' + (f.max || 100) + '" value="' + (val !== undefined && val !== null ? val : '') + '" onchange="saveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.value)" style="width: 100px; padding: 4px 8px; background: var(--bg-input); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; color: var(--text);">';
        } else {
          html += '<input type="text" value="' + (val || '').toString().replace(/"/g, '&quot;') + '" onchange="saveAgentField(\'' + preset.slug + '\',\'' + agentName + '\',\'' + f.key + '\',this.value)" style="width: 100%; padding: 4px 8px; background: var(--bg-input); border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; color: var(--text); font-size: 0.75rem;">';
        }
        html += '</div>';
      });
      html += '</div>';
    });
    grid.innerHTML = html;
  }
})();
