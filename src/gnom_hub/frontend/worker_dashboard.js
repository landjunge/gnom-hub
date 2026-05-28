/* ═══════════════════════════════════════════
   GNOM-HUB — Worker Agents Cards Rendering
   ═══════════════════════════════════════════ */

function handleWorkerClick(id) {
  if (typeof selectAgent === 'function') {
    selectAgent(id);
  }
}

function handleWorkerDblClick(id, status) {
  if (typeof toggleStatus === 'function') {
    toggleStatus(id, status);
  }
}

function renderAgentList(filter = '') {
  const el = document.getElementById('agent-list');
  if (!el) return;
  const f = filter.toLowerCase();

  let filtered = f ? agents.filter(a => a.name.toLowerCase().includes(f)) : agents;
  filtered = filtered.filter(a => !a.name.toLowerCase().includes('hermes'));

  const coreNames = ['writerag', 'coderag', 'researcherag', 'editorag'];
  const coreAgents = filtered.filter(a => coreNames.includes(a.name.toLowerCase()) && a.status !== 'sleeping');

  if (!coreAgents.length) {
    el.innerHTML = '<div class="empty">Keine Agenten.</div>';
  } else {
    const renderCard = (a) => {
      const stClass = a.status === 'busy' ? 'busy' : (a.status === 'paused' ? 'paused' : (a.status === 'online' ? 'on' : 'off'));
      const isCore = coreNames.includes(a.name.toLowerCase());
      const role = a.role && a.role !== 'normal' && !isCore ? a.role : '';
      const roleIcon = role === 'general' ? ' 👑' : role === 'summarizer' ? ' 📋' : '';
      const c = agentColor(a.name);
      return `<div class="agent-card ${stClass} ${a.id === selectedId ? 'active' : ''}" id="card-${a.id}" onclick="handleWorkerClick('${a.id}')" ondblclick="handleWorkerDblClick('${a.id}', '${a.status}')" style="--agent-color:${c};">
        <h3><span>${a.name}</span>${roleIcon}</h3>
        <div class="desc">${a.description || '–'}</div>
        <div class="meta">${a.port ? `<span class="badge port">:${a.port}</span>` : ''}${role ? `<span class="badge role ${role}">${role}</span>` : ''}</div>
      </div>`;
    };
    el.innerHTML = coreAgents.map(renderCard).join('');
  }
}

function filterAgents(q) {
  renderAgentList(q);
}
