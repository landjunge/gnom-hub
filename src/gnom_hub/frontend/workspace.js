/* ═══════════════════════════════════════════
   GNOM-HUB — Workspace Explorer & Runner
   ═══════════════════════════════════════════ */

async function showWorkspace() {
  selectedId = null;
  document.getElementById('content').innerHTML = `
    <div class="panel" id="workspace-panel" style="padding:12px 15px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px; flex-wrap:nowrap;">
        <div style="display:flex; align-items:center; gap:10px;">
          <button class="btn-primary" onclick="showWarRoom()" style="padding: 2px 6px; font-size:0.75rem;">◀ Zurück</button>
          <h2 style="margin:0; font-size:0.95rem; font-weight:600; border:none; letter-spacing:0.5px;">Workspace</h2>
        </div>
        <button class="btn-primary" onclick="loadWorkspace()" style="padding: 2px 8px; font-size:0.75rem; white-space:nowrap;">Refresh</button>
      </div>
      <div id="workspace-list"><div class="empty">Loading files...</div></div>
    </div>
  `;
  await loadWorkspace();
}

function renderWorkspaceItemHTML(f) {
  const date = new Date(f.mtime * 1000).toLocaleString('en-US', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const ext = f.name.split('.').pop().toLowerCase();
  const isWeb = ['html', 'htm', 'css', 'js', 'svg'].includes(ext);
  const isPy = ext === 'py';
  let actionBtn = '';
  if (isWeb) {
    actionBtn = `<button class="btn-primary" onclick="event.stopPropagation(); openWorkspaceFile('${f.name}')" title="Im Browser öffnen">🌐 Open</button>
    <button class="btn-primary" onclick="event.stopPropagation(); previewWorkspaceFile('${f.name}')" title="Live Preview">👁️ Preview</button>`;
  } else if (isPy) {
    actionBtn = `<button class="btn-primary" onclick="event.stopPropagation(); runWorkspaceFile('${f.name}')" title="Python ausführen">▶ Run</button>`;
  }
  return `<div class="mem-item" style="display:flex; justify-content:space-between; align-items:center;">
    <div style="cursor:pointer; flex:1;" onclick="readWorkspaceFile('${f.name}')">
      <strong style="color:rgba(255,255,255,0.95); font-weight:500;">${f.name}</strong> 
      <span style="font-size:0.8em;color:var(--text-dim);margin-left:10px;">${f.size} Bytes</span>
    </div>
    <div style="display:flex; align-items:center; gap:10px;">
      <span style="font-size:0.75rem; color:var(--text-muted);">${date}</span>
      ${actionBtn}
    </div>
  </div>`;
}

async function loadWorkspace() {
  const list = document.getElementById('workspace-list');
  if (!list) return;
  const files = await api('GET', '/workspace');
  const projRes = await api('GET', '/project');
  const projName = projRes && projRes.project ? projRes.project : 'default';

  const panelTitle = document.querySelector('#workspace-panel h2');
  if (panelTitle) {
    panelTitle.innerHTML = `📁 gnom_workspace / <span style="color:var(--green)">${projName}</span> <div class="actions"><button class="btn-primary" onclick="loadWorkspace()">Refresh</button></div>`;
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
      <iframe src="/api/workspace/${name}/serve" sandbox="allow-scripts allow-same-origin" style="flex:1; border:none; background:white; width:100%; height:100%;"></iframe>
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
      <pre style="flex-grow:1; overflow:auto; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:var(--radius); padding:10px; font-family:monospace; white-space:pre-wrap; max-height:60vh;">${res.stdout || '(keine Ausgabe)'}</pre>
      ${hasErr ? `<pre style="margin-top:8px; background:#1a0000; color:#ff6666; border:1px solid #ff4444; border-radius:var(--radius); padding:10px; font-family:monospace; white-space:pre-wrap; max-height:20vh; overflow:auto;">STDERR:\n${res.stderr}</pre>` : ''}
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
        <textarea readonly style="flex-grow:1; background:var(--bg-input); color:var(--text); border:1px solid var(--border); border-radius:var(--radius); padding:10px; font-family:monospace; resize:none;">${res.content}</textarea>
      </div>
    `;
    document.body.appendChild(modal);
  } else {
    toast("Fehler beim Lesen der Datei", "error");
  }
}
