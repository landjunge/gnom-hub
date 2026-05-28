/* ═══════════════════════════════════════════
   GNOM-HUB — War Room Chat & Autocomplete
   ═══════════════════════════════════════════ */

const BUILTIN_CMDS = ['bs', 'research', 'job', 'status', 'clear', 'free', 'project', 'git', 'tts', 'worker', 'system', 'all'];
var acIdx = -1;

// TTS Queue State
const _ttsQ = [];
var _ttsBusy = false;

// STT Recognition State
let recognition;
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.continuous = true;
  recognition.lang = 'de-DE';
  recognition.onresult = (e) => {
    let text = '';
    for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript + ' ';
    const inp = document.getElementById('chat-input');
    if (inp) inp.value = text.trim();
  };
  recognition.onerror = () => {
    const b = document.getElementById('mic-btn');
    if (b) { b.classList.remove('active'); b.innerText = 'Rec'; }
  };
  recognition.onend = () => {
    const b = document.getElementById('mic-btn');
    if (b) { b.classList.remove('active'); b.innerText = 'Rec'; }
  };
}

function buildChatHintsHTML() {
  return `
    <div style="font-size:0.60rem; color:var(--text-dim); margin-top:8px; display:flex; gap:16px; align-items:center; padding: 2px 4px;">
      <span><strong>@</strong> Direct agent task (e.g. @bs, @research, @coderag)</span>
      <span><strong>@@</strong> System-level command (e.g. @@project, @@status, @@git)</span>
    </div>
    <div class="chat-hints">
      <span data-tooltip="Brainstorm: Activate the swarm for complex ideas.">@bs</span>
      <span data-tooltip="Research: Start an autonomous research job.">@research</span>
      <span data-tooltip="Job Task: Distribute background tasks to agents.">@job</span>
      <span data-tooltip="Free: Clear active jobs from an agent.">@free</span>
      <span data-tooltip="Worker: Query all non-system agents.">@worker</span>
      <span data-tooltip="System: Query all system-level agents.">@system</span>
      <span data-tooltip="All: Query all online agents.">@all</span>
      <span data-tooltip="Project: (e.g. @@project netzwerkpunkt, @@project delete netzwerkpunkt)">@@project</span>
      <span data-tooltip="Clear: (@@clear chat, @@clear @project, @@clear all agents)">@@clear</span>
      <span data-tooltip="Status: Get system and agent status.">@@status</span>
      <span data-tooltip="Git: Run git commands (e.g. @@git status)">@@git</span>
      <span data-tooltip="Coffee break: (Animation)">/coffee</span>
      <span data-tooltip="UFO Event: (Animation)">/ufo</span>
      <span data-tooltip="Ghost: (Animation)">/ghost</span>
    </div>`;
}

function buildWarRoomHTML() {
  const ttsChecked = document.getElementById('tts-enabled')?.checked ?? false;
  return `<div class="panel" id="war-room">
    <h2 style="display:flex; align-items:center;">War Room <span id="project-indicator" style="font-size:0.75rem; color:var(--text-muted); background:rgba(255,255,255,0.05); padding:3px 8px; border-radius:12px; margin-left:10px; border:1px solid rgba(255,255,255,0.1);">MAIN HUB</span>
      <button id="project-help-btn" onclick="const e=document.getElementById('project-explanation'); e.style.display = e.style.display==='none' ? 'block' : 'none';" style="display:none; margin-left:8px; padding:3px 8px; font-size:0.7rem; border-radius:12px; border:1px solid var(--green); background:rgba(57,255,20,0.1); color:var(--green); cursor:pointer;">ℹ️ Info</button>
    </h2>
    <div id="project-explanation" style="display:none; font-size:0.8rem; color:#fff; background:rgba(61,220,132,0.1); border-left:3px solid var(--green); padding:10px 14px; margin-bottom:12px; border-radius:4px; line-height:1.5;"></div>
    <div id="chat-display"></div>
    <div class="chat-bar">
      <div class="chat-input-wrap">
        <div class="ac-dropdown" id="ac-dropdown"></div>
        <textarea id="chat-input" placeholder="@bs @research @idea …" oninput="onChatInput(this)" onkeydown="onChatKey(event)"></textarea>
      </div>
      <button class="btn-primary" onclick="sendChat()" style="padding:0 20px;">Send</button>
      <input type="checkbox" id="tts-enabled" style="display:none;" ${ttsChecked ? 'checked' : ''}>
      <button id="mic-btn" class="btn-mic" onclick="toggleSTT()" title="Voice Input" style="padding:0 14px;">Rec</button>
    </div>
    ${buildChatHintsHTML()}
  </div>`;
}

function showWarRoom() {
  selectedId = null;
  window._lastChatData = '';
  const searchInput = document.getElementById('agent-search');
  if (typeof renderAgentList === 'function') {
    renderAgentList(searchInput ? searchInput.value : '');
  }
  document.getElementById('content').innerHTML = buildWarRoomHTML();
  updateProjectIndicator();
  refreshChat();
}

function onChatInput(ta) {
  const dd = document.getElementById('ac-dropdown');
  if (!dd) return;
  const val = ta.value, m = val.match(/@(\w*)$/);
  if (!m) { dd.classList.remove('show'); return; }
  const q = m[1].toLowerCase();
  const agentNames = agents.map(a => a.name);
  const all = [...BUILTIN_CMDS, ...agentNames].filter(n => n.toLowerCase().startsWith(q));
  if (!all.length || (all.length === 1 && all[0].toLowerCase() === q)) { dd.classList.remove('show'); return; }
  acIdx = -1;
  dd.innerHTML = all.map(n => `<div class="ac-item" onmousedown="pickAc('${n}')">${BUILTIN_CMDS.includes(n) ? '@' + n : '@ ' + n}</div>`).join('');
  dd.classList.add('show');
}

function pickAc(name) {
  const ta = document.getElementById('chat-input');
  ta.value = ta.value.replace(/@\w*$/, '@' + name + ' ');
  document.getElementById('ac-dropdown').classList.remove('show');
  ta.focus();
}

function onChatKey(e) {
  const dd = document.getElementById('ac-dropdown');
  if (!dd) return;
  const items = dd.querySelectorAll('.ac-item');
  if (dd.classList.contains('show') && items.length) {
    if (e.key === 'ArrowDown') { e.preventDefault(); acIdx = Math.min(acIdx + 1, items.length - 1); items.forEach((el, i) => el.classList.toggle('active', i === acIdx)); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); acIdx = Math.max(acIdx - 1, 0); items.forEach((el, i) => el.classList.toggle('active', i === acIdx)); return; }
    if (e.key === 'Tab') { e.preventDefault(); pickAc(items[acIdx >= 0 ? acIdx : 0]?.textContent.replace(/^@\s?/, '') || ''); return; }
    if (e.key === 'Enter' && acIdx >= 0) { e.preventDefault(); pickAc(items[acIdx]?.textContent.replace(/^@\s?/, '') || ''); return; }
    if (e.key === 'Escape') { dd.classList.remove('show'); return; }
  } else {
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      const ta = document.getElementById('chat-input');
      if (ta) {
        try {
          const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
          if (history.length > 0) {
            if (window.chatHistoryIdx === undefined) {
              window.chatHistoryIdx = -1;
              window.chatHistoryDraft = "";
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault();
              if (window.chatHistoryIdx === -1) {
                window.chatHistoryDraft = ta.value;
                window.chatHistoryIdx = history.length - 1;
              } else if (window.chatHistoryIdx > 0) {
                window.chatHistoryIdx--;
              } else {
                return;
              }
              ta.value = history[window.chatHistoryIdx];
              ta.selectionStart = ta.selectionEnd = ta.value.length;
            } else if (e.key === 'ArrowDown') {
              e.preventDefault();
              if (window.chatHistoryIdx === -1) {
                return;
              } else if (window.chatHistoryIdx < history.length - 1) {
                window.chatHistoryIdx++;
                ta.value = history[window.chatHistoryIdx];
              } else {
                window.chatHistoryIdx = -1;
                ta.value = window.chatHistoryDraft;
              }
              ta.selectionStart = ta.selectionEnd = ta.value.length;
            }
          }
        } catch (err) {
          console.error(err);
        }
      }
    }
  }
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
}

function handleShowboxSpeedCommand(m, ta) {
  const speedVal = parseFloat(m.substring(15).trim());
  if (!isNaN(speedVal) && speedVal > 0) {
    window.showboxSpeed = speedVal * 1000;
    if (window.activeShowboxIndex >= 0 && window.showboxActive) {
      const idx = window.activeShowboxIndex;
      window.closeShowbox();
      setTimeout(() => window.triggerShowbox(idx), 100);
    }
    toast(`Showbox Speed: ${speedVal}s`, 'success');
  } else {
    toast('Ungültiger Speed-Wert!', 'error');
  }
  ta.value = '';
}

function handleShowboxLoadCommand(m, ta) {
  const showName = m.substring(9).trim();
  if (window.activeShowboxIndex >= 0) {
    const s = document.createElement('script');
    s.src = showName + '.js';
    s.onload = () => {
      if (window.loadedShowbox) {
        const idx = window.activeShowboxIndex;
        window.showboxes[idx] = window.loadedShowbox;
        window.closeShowbox();
        setTimeout(() => window.triggerShowbox(idx), 100);
      }
    };
    document.head.appendChild(s);
    toast(`Loading Showbox: ${showName}`, 'success');
  } else {
    toast('Please activate a Showbox first!', 'error');
  }
  ta.value = '';
}

function handleChatCommands(msg, ta) {
  const m = msg.toLowerCase();
  if (m === '@tts on') { const cb = document.getElementById('tts-enabled'); if (cb) cb.checked = true; ta.value = ''; toast('🗣️ TTS Aktiviert', 'success'); return true; }
  if (m === '@tts off') { const cb = document.getElementById('tts-enabled'); if (cb) cb.checked = false; stopTTS(); ta.value = ''; toast('🔇 TTS Deaktiviert', 'info'); return true; }
  if (m === '@tts') { const cb = document.getElementById('tts-enabled'); if (cb) { cb.checked = !cb.checked; if (!cb.checked) stopTTS(); toast(cb.checked ? '🗣️ TTS Aktiviert' : '🔇 TTS Deaktiviert', cb.checked ? 'success' : 'info'); } ta.value = ''; return true; }
  if (m === '/ufo') { if (window.showUfoAttack) window.showUfoAttack(); return true; }
  if (m === '/ghost') { if (window.showGhost) window.showGhost(); return true; }
  if (m === '/coffee') { if (window.showCoffeeBreak) window.showCoffeeBreak(); return true; }
  if (m.startsWith('@showbox speed ')) {
    handleShowboxSpeedCommand(m, ta);
    return true;
  }
  if (m.startsWith('@showbox ')) {
    handleShowboxLoadCommand(m, ta);
    return true;
  }
  return false;
}

function addToChatHistory(msg) {
  if (!msg) return;
  try {
    let history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    if (history.length === 0 || history[history.length - 1] !== msg) {
      history.push(msg);
      if (history.length > 50) history.shift();
      localStorage.setItem('chatHistory', JSON.stringify(history));
    }
  } catch (e) {
    console.error(e);
  }
  window.chatHistoryIdx = -1;
  window.chatHistoryDraft = "";
}

async function sendChat() {
  const ta = document.getElementById('chat-input');
  if (!ta) return;
  const msg = ta.value.trim();
  if (!msg) return;
  addToChatHistory(msg);
  if (handleChatCommands(msg, ta)) return;
  ta.value = '';

  document.getElementById('ac-dropdown')?.classList.remove('show');
  const res = await api('POST', '/chat', { content: msg });
  if (res) {
    if (res.status === 'role_set') toast(`👑 ${res.agent} → ${res.role}`, 'success');
    else if (res.status === 'idea_saved') toast('💡 Idea saved', 'success');
    else if (res.status === 'job_created') toast(`📋 Job → ${res.general}: ${res.task?.substring(0, 60)}`, 'success');
    else if (res.msg) toast(`⚠️ ${res.msg}`, 'error');
    else if (res.status === 'cleared') toast('🗑 Chat cleared', 'success');
    else if (res.status === 'agents') toast(`📊 ${res.agents.map(a => a.name + '(' + a.role + ')').join(', ')}`, 'info');
    else {
      const target = res.target ? `→ ${res.target}` : `→ ${(res.asked || []).join(', ') || 'nobody'}`;
      toast(`${res.mode === 'brainstorm' ? '🧠' : res.mode === 'research' ? '🔍' : '💬'} ${target}`, 'success');
    }
    refreshChat();
    if (typeof loadAgents === 'function') loadAgents();
    updateProjectIndicator();
  } else {
    toast('Hub unreachable', 'error');
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function parseShowboxInMsg(m) {
  let rawContent = m.content || "";
  let showBoxFound = false;
  let showData = null;
  const showboxMatch = rawContent.match(/<SHOWBOX(?::(\d+))?>([\s\S]*?)<\/SHOWBOX>/);
  const mid = m.id || Math.random().toString(36).slice(2);
  
  if (showboxMatch) {
    showBoxFound = true;
    rawContent = rawContent.replace(showboxMatch[0], '').trim();
    if (!window._processedShowboxes.has(mid)) {
      window._processedShowboxes.add(mid);
      try { 
        showData = JSON.parse(showboxMatch[2]); 
        if (showboxMatch[1] !== undefined) {
          showData._targetIdx = parseInt(showboxMatch[1], 10) - 1;
        }
      } 
      catch(e) { console.error("SHOWBOX parse error", e); }
    }
  }
  return { rawContent, showBoxFound, showData };
}

function handleShowboxTrigger(showData, sender) {
  let slides = showData;
  if (showData && !Array.isArray(showData) && Array.isArray(showData.slides)) {
    slides = showData.slides;
    if (showData._targetIdx !== undefined) slides._targetIdx = showData._targetIdx;
  }
  if (slides && Array.isArray(slides) && slides.length > 0) {
    setTimeout(() => {
      let targetIdx = window.activeShowboxIndex >= 0 ? window.activeShowboxIndex : 0;
      if (slides._targetIdx !== undefined && slides._targetIdx >= 0 && slides._targetIdx < window.showboxes.length) {
        targetIdx = slides._targetIdx;
      }
      window.showboxes[targetIdx] = slides;
      if (window.closeShowbox) window.closeShowbox();
      setTimeout(() => { if (window.triggerShowbox) window.triggerShowbox(targetIdx, sender); }, 100);
    }, 300);
  }
}

function renderChatMessageHTML(m) {
  const isUser = m.metadata?.sender === 'user';
  const name = isUser ? 'You' : (m.metadata?.sender || 'System');
  const time = m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : '';
  const c = isUser ? 'var(--primary)' : agentColor(name);
  const nameColor = isUser ? 'var(--primary)' : (name.toLowerCase().startsWith('testag') ? '#0066FF' : 'inherit');
  const mid = m.id || Math.random().toString(36).slice(2);
  
  const { rawContent, showBoxFound, showData } = parseShowboxInMsg(m);
  let safe = esc(rawContent);
  if (showBoxFound) {
    const targetText = (showData && showData._targetIdx !== undefined) ? ` Button ${showData._targetIdx + 1}` : '';
    safe += `<div style="color:var(--cyan);font-size:0.8em;margin-top:8px;">[ 🎬 Showbox Triggered${targetText} ]</div>`;
  }
  
  handleShowboxTrigger(showData, name);

  safe = safe.replace(/&lt;think&gt;([\s\S]*?)&lt;\/think&gt;/gi, function(match, p1) {
    return `<details class="think-block" open>
      <summary>Denkprozess anzeigen...</summary>
      <div class="think-content">${p1.trim()}</div>
    </details>`;
  });
  safe = safe.replace(/\[SOUL:\s*([\s\S]*?)\]/g, '<div style="font-size:0.6rem; color:var(--bg-surface); opacity:0.5; margin-top:4px;">[SOUL: $1]</div>');
  safe = safe.replace(/\n/g, '<br>');
  return `<div class="chat-msg ${isUser ? 'user' : 'agent'}" style="border-left-color:${c};">
    <div class="chat-meta"><span class="agent-name" style="color:${nameColor}">${esc(name)}</span><span><button class="copy-btn" onclick="copyMsg('${mid}')" title="Copy">📋</button><button class="copy-btn del-btn" onclick="deleteChatMsg('${mid}')" title="Delete">🗑</button>${time}</span></div>
    <div class="mem-content" id="msg-${mid}">${safe}</div></div>`;
}

async function refreshChat() {
  const el = document.getElementById('chat-display');
  if (!el) return;
  const msgs = await api('GET', '/chat?limit=20');

  const dataStr = JSON.stringify(msgs || []);
  if (window._lastChatData === dataStr) return;
  window._lastChatData = dataStr;

  const st = el.scrollTop;
  const wasAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;

  if (!msgs || !msgs.length) { el.innerHTML = '<div class="empty">No messages yet.</div>'; return; }
  const sorted = msgs.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
  window._processedShowboxes = window._processedShowboxes || new Set();

  el.innerHTML = sorted.map(renderChatMessageHTML).join('');

  if (wasAtBottom || !window._chatInitialized) {
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    window._chatInitialized = true;
  } else {
    el.scrollTop = st;
  }

  if (!window._spokenIds) window._spokenIds = new Set();
  sorted.filter(m => m.metadata?.sender !== 'user' && !window._spokenIds.has(m.id)).forEach(m => {
    window._spokenIds.add(m.id);
    speak(`${m.metadata?.sender || 'System'} sagt: ${m.content}`, m.metadata?.sender || 'System');
  });
}

function copyMsg(id) {
  const el = document.getElementById('msg-' + id);
  if (!el) return;
  navigator.clipboard.writeText(el.innerText).then(() => {
    const btn = el.parentElement.querySelector('.copy-btn');
    if (btn) { btn.textContent = '✅'; setTimeout(() => btn.textContent = '📋', 1200); }
  });
}

function stopTTS() {
  speechSynthesis.cancel();
  _ttsQ.length = 0;
  _ttsBusy = false;
  const btn = document.getElementById('stop-tts-btn');
  if (btn) btn.style.display = 'none';
}

async function deleteChatMsg(id) {
  await api('DELETE', `/memory/${id}`);
  stopTTS();
  window._lastChatData = null;
  refreshChat();
}

function getVoiceForAgent(agentName, lang) {
  if (typeof speechSynthesis === 'undefined') return null;
  const voices = speechSynthesis.getVoices();
  if (!voices.length) return null;
  const langPrefix = lang.split('-')[0].toLowerCase();
  let filtered = voices.filter(v => v.lang.toLowerCase().startsWith(langPrefix));
  if (!filtered.length) filtered = voices;
  let hash = 0;
  for (let i = 0; i < agentName.length; i++) {
    hash = agentName.charCodeAt(i) + ((hash << 5) - hash);
  }
  return filtered[Math.abs(hash) % filtered.length];
}

async function speak(text, agentId = '') {
  if (!document.getElementById('tts-enabled')?.checked) return;
  _ttsQ.push({ text, agentId });
  if (_ttsBusy) return;
  _ttsBusy = true;
  const stopBtn = document.getElementById('stop-tts-btn');
  if (stopBtn) stopBtn.style.display = 'block';

  while (_ttsQ.length) {
    const { text: t, agentId: a } = _ttsQ.shift();
    speechSynthesis.cancel();
    try {
      const r = await fetch(`${API}/audio/tts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: t, agent_id: a }) });
      if (r.ok && r.headers.get('content-type')?.includes('audio')) {
        const audio = new Audio(URL.createObjectURL(await r.blob()));
        await new Promise(ok => { audio.onended = ok; audio.onerror = ok; audio.play(); }); continue;
      }
    } catch { }
    const u = new SpeechSynthesisUtterance(t); u.lang = 'de-DE'; u.rate = 1.0;
    const voice = getVoiceForAgent(a || 'System', u.lang);
    if (voice) u.voice = voice;
    await new Promise(ok => { u.onend = ok; u.onerror = ok; speechSynthesis.speak(u); });
  }
  _ttsBusy = false;
  if (stopBtn) stopBtn.style.display = 'none';
}

function toggleSTT() {
  const btn = document.getElementById('mic-btn');
  if (!recognition) { toast('Browser does not support voice input', 'error'); return; }
  if (btn.classList.contains('active')) {
    recognition.stop();
    btn.classList.remove('active');
    btn.innerText = 'Rec';
  } else {
    recognition.start();
    btn.classList.add('active');
    btn.innerText = 'Stop';
  }
}

async function updateProjectIndicator() {
  const res = await api('GET', '/project');
  const p = res && res.project ? res.project : 'default';
  const ind = document.getElementById('project-indicator');
  const expl = document.getElementById('project-explanation');
  const helpBtn = document.getElementById('project-help-btn');
  if (ind) {
    if (p === 'default') {
      ind.textContent = 'MAIN HUB';
      ind.style.color = 'var(--text-muted)';
      ind.style.borderColor = 'rgba(255,255,255,0.1)';
      ind.style.background = 'rgba(255,255,255,0.05)';
      if (helpBtn) helpBtn.style.display = 'none';
      if (expl) expl.style.display = 'none';
    } else {
      ind.textContent = p.toUpperCase();
      ind.style.color = 'var(--green)';
      ind.style.borderColor = 'rgba(57,255,20,0.3)';
      ind.style.background = 'rgba(57,255,20,0.05)';
      if (helpBtn) helpBtn.style.display = 'inline-block';
    }
  }
  if (expl && p !== 'default') {
    expl.innerHTML = `🛡️ <strong>Project Mode active: ${p}</strong><br>You are in project <b>${p}</b>. Communications, files, and agent thoughts are saved exclusively for this project. If you return in 10 years, you will find everything exactly as you left it. <i>(Type <code>@project default</code> to exit the project)</i>`;
  }
}

function checkTimers() {
  const now = Date.now();
  const lastGhost = localStorage.getItem('last_ghost_time');
  if (!lastGhost) {
    localStorage.setItem('last_ghost_time', now);
  } else if (now - parseInt(lastGhost) > ((6 * 60 * 60) + (6 * 60)) * 1000) {
    localStorage.setItem('last_ghost_time', now);
    const ghostOverlay = document.getElementById('ghost-overlay');
    if (ghostOverlay) {
      const newGhost = ghostOverlay.cloneNode(true);
      ghostOverlay.parentNode.replaceChild(newGhost, ghostOverlay);
      newGhost.style.display = 'flex';
      setTimeout(() => { newGhost.style.display = 'none'; }, 120000);
    }
  }
}
