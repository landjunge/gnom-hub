/* ═══════════════════════════════════════════
   GNOM-HUB — System Dashboard (Top Bar Lamps)
   ═══════════════════════════════════════════ */

var _lastInternals = '';

function findAgentByName(name) {
  return agents.find(a => a.name.toLowerCase() === name.toLowerCase());
}

function handleAgentClick(name) {
  const agent = findAgentByName(name);
  if (agent) {
    if (typeof selectAgent === 'function') {
      selectAgent(agent.id);
    }
  }
}

async function handleAgentDblClick(name) {
  const agent = findAgentByName(name);
  if (agent) {
    if (typeof toggleStatus === 'function') {
      await toggleStatus(agent.id, agent.status);
    }
  }
}

// ── Status Lamps ──
function updateLamps(hubAgents) {
  const el = document.getElementById('status-lamps');
  if (!el || !hubAgents) return;

  // 4 System-Agenten als Lämpchen
  const sysNames = ['soulag', 'generalag', 'securityag', 'watchdogag'];
  const hiddenSys = [
    { name: 'SoulAG', status: 'online' },
    { name: 'GeneralAG', status: 'online' },
    { name: 'SecurityAG', status: 'online' },
    { name: 'WatchdogAG', status: 'online' }
  ];

  let displayAgents = [...hiddenSys.filter(h => !hubAgents.some(a => a.name === h.name)), ...hubAgents];
  displayAgents = displayAgents.filter(a => sysNames.includes((a.name || '').toLowerCase()));

  const names = displayAgents.map(a => a.name).join(',');

  if (_lastInternals !== names) {
    el.innerHTML = displayAgents.map((a, i) => {
      const dur = (2.5 + Math.random() * 2.0).toFixed(2);
      const dly = (-(Math.random() * 6.0)).toFixed(2);
      const col = agentColor(a.name);
      return `<div class="sys-agent-card" data-ag="${a.name}" title="${a.name}" onclick="handleAgentClick('${a.name}')" ondblclick="handleAgentDblClick('${a.name}')" style="--agent-color:${col};--dur:${dur}s;--delay:${dly}s">${a.name}</div>`;
    }).join('');
    _lastInternals = names;
  }

  el.querySelectorAll('.sys-agent-card').forEach(l => {
    const key = l.dataset.ag;
    const agent = displayAgents.find(a => a.name === key);
    const st = agent?.status || 'offline';
    l.className = st === 'busy' ? 'sys-agent-card busy' : st === 'online' ? 'sys-agent-card on' : 'sys-agent-card off';
  });
}
