/* ═══════════════════════════════════════════
   GNOM-HUB — Workspace Explorer & Runner
   ═══════════════════════════════════════════ */

async function showWorkspace() {
  if (typeof trackView === 'function') trackView('workspace');
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="workspace-panel" style="padding:12px 15px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px; flex-wrap:nowrap;">
        <h2 style="margin:0; font-size:0.95rem; font-weight:600; border:none; letter-spacing:0.5px;">Workspace</h2>
        <button class="btn-primary" onclick="loadWorkspace()" style="padding: 2px 8px; font-size:0.75rem; white-space:nowrap;">Refresh</button>
      </div>

      <!-- Workspace-Pfad-Konfiguration -->
      <div id="workspace-config-section" style="margin-bottom:14px; padding:12px 14px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.08); border-radius:var(--radius);">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
          <label style="font-size:0.85rem; font-weight:500; color:rgba(255,255,255,0.9);">📂 Workspace-Pfad</label>
          <span id="workspace-default-badge" style="font-size:0.7rem; padding:2px 8px; border-radius:8px; background:rgba(0,229,255,0.1); color:var(--accent); display:none;">Default</span>
        </div>
        <div style="display:flex; gap:8px; align-items:stretch;">
          <input type="text" id="workspace-path-input" placeholder="~/gnom-Workspace" style="flex:1; background:var(--bg-input); border:1px solid var(--glass-border); border-radius:var(--radius-sm); color:var(--text); padding:6px 10px; font-family:var(--font-mono, monospace); font-size:0.85rem; outline:none;" />
          <button class="btn-primary" id="workspace-save-btn" onclick="saveWorkspacePath()" style="padding:0 16px; font-size:0.85rem; white-space:nowrap;">Speichern</button>
          <button class="btn-primary" id="workspace-reset-btn" onclick="resetWorkspacePath()" style="padding:0 12px; font-size:0.85rem; background:rgba(255,80,50,0.1); border-color:rgba(255,80,50,0.3); color:#f88; white-space:nowrap;" title="Auf Default ~/gnom-Workspace zurücksetzen">Reset</button>
        </div>
        <div id="workspace-config-status" style="margin-top:6px; font-size:0.78rem; min-height:1em;"></div>
      </div>

      <div id="workspace-list"><div class="empty">Loading files...</div></div>
    </div>
  `;
  await loadWorkspacePath();
  await loadWorkspace();
}

function renderWorkspaceItemHTML(f) {
  const date = new Date(f.mtime * 1000).toLocaleString('en-US', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const ext = f.name.split('.').pop().toLowerCase();
  const isWeb = ['html', 'htm', 'css', 'js', 'svg'].includes(ext);
  const isPy = ext === 'py';
  let actionBtn = '';
  if (isWeb) {
    actionBtn = `<button class="btn-primary" onclick="event.stopPropagation(); openWorkspaceFile('${escapeHtml(f.name)}')" title="Im Browser öffnen">🌐 Open</button>
    <button class="btn-primary" onclick="event.stopPropagation(); previewWorkspaceFile('${escapeHtml(f.name)}')" title="Live Preview">👁️ Preview</button>`;
  } else if (isPy) {
    actionBtn = `<button class="btn-primary" onclick="event.stopPropagation(); runWorkspaceFile('${escapeHtml(f.name)}')" title="Python ausführen">▶ Run</button>`;
  }
  return `<div class="mem-item" style="display:flex; justify-content:space-between; align-items:center;">
    <div style="cursor:pointer; flex:1;" onclick="readWorkspaceFile('${escapeHtml(f.name)}')">
      <strong style="color:rgba(255,255,255,0.95); font-weight:500;">${escapeHtml(f.name)}</strong> 
      <span style="font-size:0.8em;color:var(--text-dim);margin-left:10px;">${f.size} Bytes</span>
    </div>
    <div style="display:flex; align-items:center; gap:10px;">
      <span style="font-size:0.75rem; color:var(--text-muted);">${date}</span>
      ${actionBtn}
    </div>
  </div>`;
}

// ═══════════════════════════════════════════
// Workspace-Pfad-Konfiguration
// ═══════════════════════════════════════════

async function loadWorkspacePath() {
  const input = document.getElementById('workspace-path-input');
  const badge = document.getElementById('workspace-default-badge');
  if (!input) return;
  const cfg = await api('GET', '/api/workspace/config');
  if (cfg && cfg.path) {
    input.value = cfg.path;
    input.placeholder = cfg.default || '~/gnom-Workspace';
    if (cfg.is_default && badge) {
      badge.style.display = 'inline-block';
      badge.textContent = 'Default';
    } else if (badge) {
      badge.style.display = 'inline-block';
      badge.textContent = 'Custom';
      badge.style.background = 'rgba(168, 85, 247, 0.1)';
      badge.style.color = '#a855f7';
    }
  }
}

window.saveWorkspacePath = async function() {
  const input = document.getElementById('workspace-path-input');
  const status = document.getElementById('workspace-config-status');
  const saveBtn = document.getElementById('workspace-save-btn');
  if (!input) return;
  const newPath = input.value.trim();
  if (!newPath) {
    if (status) { status.style.color = '#f88'; status.textContent = '⚠ Pfad darf nicht leer sein.'; }
    return;
  }
  if (saveBtn) saveBtn.disabled = true;
  if (status) { status.style.color = 'var(--text-dim)'; status.textContent = 'Speichere…'; }
  const res = await api('PUT', '/api/workspace/config', { path: newPath });
  if (saveBtn) saveBtn.disabled = false;
  if (res && res.ok) {
    if (status) {
      status.style.color = 'var(--green)';
      status.textContent = '✓ Workspace-Pfad gesetzt: ' + res.path;
    }
    await loadWorkspace();
    await loadWorkspacePath();
  } else if (res && res.detail) {
    if (status) {
      status.style.color = '#f88';
      status.textContent = '⚠ ' + res.detail;
    }
  } else {
    if (status) {
      status.style.color = '#f88';
      status.textContent = '⚠ Unbekannter Fehler beim Speichern.';
    }
  }
};

window.resetWorkspacePath = async function() {
  const status = document.getElementById('workspace-config-status');
  if (status) { status.style.color = 'var(--text-dim)'; status.textContent = 'Setze zurück…'; }
  const res = await api('POST', '/api/workspace/config/reset');
  if (res && res.ok) {
    if (status) {
      status.style.color = 'var(--green)';
      status.textContent = '✓ Auf Default zurückgesetzt: ' + res.path;
    }
    await loadWorkspace();
    await loadWorkspacePath();
  }
};

async function loadWorkspace() {
  const list = document.getElementById('workspace-list');
  if (!list) return;
  const files = await api('GET', '/workspace');
  const projRes = await api('GET', '/project');
  const projName = projRes && projRes.project ? projRes.project : 'default';

  const panelTitle = document.querySelector('#workspace-panel h2');
  if (panelTitle) {
    panelTitle.innerHTML = `📁 gnom_workspace / <span style="color:var(--green)">${escapeHtml(projName)}</span> <div class="actions"><button class="btn-primary" onclick="loadWorkspace()">Refresh</button></div>`;
  }

  if (!files || files.error) {
    list.innerHTML = '<div class="empty">Error loading workspace.</div>';
    return;
  }
  if (files.length === 0) {
    list.innerHTML = '<div class="empty">This project folder is empty.</div>';
    return;
  }
  list.innerHTML = files.map(renderWorkspaceItemHTML).join('');
}

function openWorkspaceFile(name) {
  window.open(`/api/workspace/${name}/serve`, '_blank');
}

function previewWorkspaceFile(name) {
  const modal = document.createElement('div');
  modal.className = 'modal-backdrop';
  modal.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:9999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px);";
  modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
  modal.innerHTML = `
    <div class="panel" style="width:90%; height:90%; display:flex; flex-direction:column; background:var(--bg-card); border:1px solid rgba(255,255,255,0.1); border-radius:var(--radius); box-shadow:0 20px 50px rgba(0,0,0,0.8); overflow:hidden;">
      <div style="padding:15px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.1);">
        <h2 style="margin:0; font-size:1.2rem; display:flex; align-items:center; gap:8px;">🌐 Live Preview: <span style="color:var(--primary);">${name}</span></h2>
        <div style="display:flex; gap:10px;">
          <button onclick="window.open('/api/workspace/${name}/serve', '_blank')" style="font-size:0.75rem;">Open in Tab ↗</button>
          <button onclick="this.closest('.modal-backdrop').remove()" class="btn-danger" style="font-size:0.75rem; padding:4px 10px;">Close</button>
        </div>
      </div>
      <iframe src="/api/workspace/${name}/serve" sandbox="allow-scripts" style="flex:1; border:none; background:white; width:100%; height:100%;"></iframe>
    </div>
  `;
  document.body.appendChild(modal);
}

async function runWorkspaceFile(name) {
  toast('Starte ' + name + '...', 'info');
  const res = await api('POST', `/workspace/${name}/run`);
  if (!res) { toast('Ausführung fehlgeschlagen', 'error'); return; }
  const modal = document.createElement('div');
  modal.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;";
  const hasErr = res.stderr && res.stderr.trim();
  const statusColor = res.code === 0 ? 'var(--green)' : '#ff4444';
  modal.innerHTML = `
    <div class="panel" style="width:70%; max-height:80%; display:flex; flex-direction:column;">
      <h2>▶ ${name} <span style="color:${statusColor};font-size:0.8em;">Exit: ${res.code}</span> <button onclick="this.parentElement.parentElement.parentElement.remove()" style="float:right">X</button></h2>
      <pre style="flex-grow:1; overflow:auto; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:var(--radius); padding:10px; font-family:monospace; white-space:pre-wrap; max-height:60vh;">${escapeHtml(res.stdout) || '(keine Ausgabe)'}</pre>
      ${hasErr ? `<pre style="margin-top:8px; background:#1a0000; color:#ff6666; border:1px solid #ff4444; border-radius:var(--radius); padding:10px; font-family:monospace; white-space:pre-wrap; max-height:20vh; overflow:auto;">STDERR:\n${escapeHtml(res.stderr)}</pre>` : ''}
    </div>
  `;
  document.body.appendChild(modal);
}

async function readWorkspaceFile(name) {
  const res = await api('GET', `/workspace/${name}`);
  if (res && res.content !== undefined) {
    const modal = document.createElement('div');
    modal.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;";
    modal.innerHTML = `
      <div class="panel" style="width:80%; height:80%; display:flex; flex-direction:column;">
        <h2>${name} <button onclick="this.parentElement.parentElement.parentElement.remove()" style="float:right">X</button></h2>
        <textarea readonly style="flex-grow:1; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:var(--radius); padding:10px; font-family:monospace; resize:none;">${escapeHtml(res.content)}</textarea>
      </div>
    `;
    document.body.appendChild(modal);
  } else {
    toast("Fehler beim Lesen der Datei", "error");
  }
}
