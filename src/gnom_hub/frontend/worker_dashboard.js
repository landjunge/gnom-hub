/* ═══════════════════════════════════════════
   GNOM-HUB — Worker Agents Cards Rendering
   ═══════════════════════════════════════════ */

function handleWorkerClick(id) {
  if (typeof showAgentTuning === 'function') {
    showAgentTuning(id);
  } else if (typeof selectAgent === 'function') {
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
  coreAgents.sort((a, b) => coreNames.indexOf(a.name.toLowerCase()) - coreNames.indexOf(b.name.toLowerCase()));

  if (!coreAgents.length) {
    el.innerHTML = '<div class="empty">Keine Agenten.</div>';
  } else {
    const renderCard = (a) => {
      const stClass = a.status === 'busy' ? 'busy' : (a.status === 'paused' ? 'paused' : (a.status === 'online' ? 'on' : 'off'));
      const isCore = coreNames.includes(a.name.toLowerCase());
      const role = a.role && a.role !== 'normal' && !isCore ? a.role : '';
      const roleIcon = role === 'general' ? ' 👑' : role === 'summarizer' ? ' 📋' : '';
      const c = agentColor(a.name);
      const dur = (2.5 + Math.random() * 2.0).toFixed(2);
      const dly = (-(Math.random() * 6.0)).toFixed(2);
      
      let statusLabel = 'Offline';
      if (a.status === 'busy') statusLabel = 'Beschäftigt (Busy) 🟡';
      else if (a.status === 'paused') statusLabel = 'Pausiert 🟠';
      else if (a.status === 'online') statusLabel = 'Online 🟢';
      
      const meta = typeof window.getAgentMeta === 'function' ? window.getAgentMeta(a.name) : { name: a.name, desc: a.description };
      const displayName = meta.name;
      const displayDesc = meta.desc;
      
      const helpTitle = `${displayName} (${statusLabel})`;
      const helpText = typeof getAgentHelpText === 'function' ? getAgentHelpText(a.name, a.description) : (displayDesc || 'Ein Agent im Gnom-Hub.');
      
      const icon = (typeof window.agentIcon === 'function') ? window.agentIcon(a.name) : '';
      const helpDataArt = 'data-help-art="' + a.name + '"';
      return `<div class="agent-card ${stClass} ${a.id === selectedId ? 'active' : ''}" id="card-${a.id}" onclick="handleWorkerClick('${a.id}')" ondblclick="handleWorkerDblClick('${a.id}', '${a.status}')" onmouseenter="if(window.triggerAgentArtShow) window.triggerAgentArtShow('${a.name}')" style="--agent-color:${c}; --dur:${dur}s; --delay:${dly}s;" data-help-title="${helpTitle.replace(/"/g, '&quot;')}" data-help="${helpText.replace(/"/g, '&quot;')}">
        <h3><span style="display:inline-flex;width:14px;height:14px;vertical-align:middle;color:${c};margin-right:5px;">${icon}</span><span>${displayName}</span>${roleIcon}</h3>
        <div class="desc">${displayDesc || '–'}</div>
        <div class="meta">${a.port ? `<span class="badge port">:${a.port}</span>` : ''}${role ? `<span class="badge role ${role}">${role}</span>` : ''}</div>
      </div>`;
    };
    el.innerHTML = coreAgents.map(renderCard).join('');
  }
}

function filterAgents(q) {
  renderAgentList(q);
}
