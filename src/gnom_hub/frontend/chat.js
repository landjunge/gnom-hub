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
      <span data-help-title="🧠 Brainstorming (@bs)" data-help="Der @bs Befehl aktiviert den gesamten Schwarm für komplexe Brainstorming- und Planungsaufgaben. Mehrere Agenten diskutieren und arbeiten zusammen, um eine optimale Lösung zu erarbeiten." data-tooltip="Brainstorm: Activate the swarm for complex ideas.">@bs</span>
      <span data-help-title="🔍 Research (@research)" data-help="Der @research Befehl startet einen autonomen Forschungs- und Recherche-Job. Der ResearcherAG sucht im Web und in lokalen Dokumenten nach Fakten und bereitet diese übersichtlich auf." data-tooltip="Research: Start an autonomous research job.">@research</span>
      <span data-help-title="📋 Job Task (@job)" data-help="Der @job Befehl verteilt Aufgaben an Hintergrund-Agenten. Ideal, um parallele Arbeitsschritte zu koordinieren und auszuführen." data-tooltip="Job Task: Distribute background tasks to agents.">@job</span>
      <span data-help-title="🧹 Free Agent (@free)" data-help="Der @free Befehl bricht alle aktuell laufenden Hintergrundprozesse und Aufgaben eines bestimmten Agenten ab und setzt ihn wieder in den Standby-Zustand." data-tooltip="Free: Clear active jobs from an agent.">@free</span>
      <span data-help-title="👷 Worker (@worker)" data-help="Mit dem @worker Befehl sprichst du gezielt alle ausführenden Worker-Agenten (CoderAG, WriterAG, ResearcherAG, EditorAG) an." data-tooltip="Worker: Query all non-system agents.">@worker</span>
      <span data-help-title="⚙️ System (@system)" data-help="Mit dem @system Befehl sprichst du die koordinierenden System-Agenten (GeneralAG, SoulAG, WatchdogAG) an." data-tooltip="System: Query all system-level agents.">@system</span>
      <span data-help-title="🌐 All (@all)" data-help="Der @all Befehl sendet deine Nachricht an alle online verfügbaren Agenten im System gleichzeitig." data-tooltip="All: Query all online agents.">@all</span>
      <span data-help-title="📂 Project Management (@@project)" data-help="Verwalte deine Projekte im Hub. Nutze '@@project <name>' um ein Projekt zu erstellen oder zu wechseln, und '@@project delete <name>' zum Löschen." data-tooltip="Project: (e.g. @@project netzwerkpunkt, @@project delete netzwerkpunkt)">@@project</span>
      <span data-help-title="🗑️ Clear Hub (@@clear)" data-help="Löscht ausgewählte Verläufe oder Daten: '@@clear chat' leert den Chatverlauf, '@@clear all agents' setzt alle Agenten-Speicher zurück." data-tooltip="Clear: (@@clear chat, @@clear @project, @@clear all agents)">@@clear</span>
      <span data-help-title="📊 System Status (@@status)" data-help="Ruft den aktuellen Systemstatus ab. Zeigt CPU-, RAM-, Docker- und Netzwerkmetriken sowie den Zustand der Agenten." data-tooltip="Status: Get system and agent status.">@@status</span>
      <span data-help-title="🐙 Git Integration (@@git)" data-help="Ermöglicht das Ausführen von Git-Befehlen direkt im Hub-Arbeitsverzeichnis, z.B. '@@git status', '@@git log' oder '@@git commit'." data-tooltip="Git: Run git commands (e.g. @@git status)">@@git</span>
      <span data-help-title="☕ Kaffeepause (/coffee)" data-help="Löst eine gemütliche Kaffeepausen-Animation im War Room aus. Perfekt für kurze Verschnaufpausen." data-tooltip="Coffee break: (Animation)">/coffee</span>
      <span data-help-title="🛸 UFO-Sichtung (/ufo)" data-help="Fliegt ein UFO über deinen Bildschirm? Dieser Animationsbefehl sorgt für außerirdische Abwechslung." data-tooltip="UFO Event: (Animation)">/ufo</span>
      <span data-help-title="👻 Geisterstunde (/ghost)" data-help="Ruft einen geheimnisvollen Geist herbei, der durch dein Dashboard schwebt." data-tooltip="Ghost: (Animation)">/ghost</span>
    </div>`;
}

function buildWarRoomHTML() {
  const ttsChecked = localStorage.getItem('ttsEnabled') !== 'false';
  return `<div class="panel" id="war-room">
    <h2 style="display:flex; align-items:center; justify-content:space-between; width: 100%;">
      <div style="display:flex; align-items:center; gap: 8px;">
        War Room 
        <span id="project-indicator" style="font-size:0.75rem; color:var(--text-muted); background:rgba(255,255,255,0.05); padding:3px 8px; border-radius:12px; margin-left:10px; border:1px solid rgba(255,255,255,0.1);" data-help-title="📂 Aktives Projekt" data-help="Gibt das aktuell ausgewählte Projekt im Hub an. Alle generierten Dateien und Shell-Befehle werden in diesem Verzeichnis ausgeführt.">MAIN HUB</span>
        <button id="project-help-btn" onclick="const e=document.getElementById('project-explanation'); e.style.display = e.style.display==='none' ? 'block' : 'none';" style="display:none; margin-left:8px; padding:3px 8px; font-size:0.7rem; border-radius:12px; border:1px solid var(--green); background:rgba(57,255,20,0.1); color:var(--green); cursor:pointer;">ℹ️ Info</button>
      </div>
    </h2>
    <div id="project-explanation" style="display:none; font-size:0.8rem; color:#fff; background:rgba(61,220,132,0.1); border-left:3px solid var(--green); padding:10px 14px; margin-bottom:12px; border-radius:4px; line-height:1.5;"></div>
    
    <!-- Split chat layout -->
    <div id="chat-split-container">
      <!-- Top Pane: Thinking Processes -->
      <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--cyan); display: flex; align-items: center; justify-content: space-between; font-weight: bold; margin-bottom: -4px;" data-help-title="🧠 Denkprozess-Fenster" data-help="Hier werden die 'Gedankengänge' (Chain of Thought) der Agenten live eingeblendet, während sie an einer Lösung arbeiten. So bleibt die Entscheidungsfindung transparent.">
        <span>🧠 Denkprozesse & Logik</span>
      </div>
      <div id="thought-display" data-help-title="🧠 Denkprozesse & Logik" data-help="Dieses Fenster zeigt dir live die interne Logik und Lösungsfindung der Agenten. Schalte oben auf 'Kompakt' oder 'Minimal', um die Anzeige anzupassen oder auszublenden."></div>
      
      <!-- Splitter / Separator -->
      <div style="display: flex; align-items: center; gap: 8px;">
        <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.08);"></div>
        <span style="font-size: 0.65rem; color: var(--text-muted); white-space: nowrap; text-transform: uppercase; letter-spacing: 0.5px;" data-help-title="💬 Chat-Verlauf" data-help="Zeigt den Dialogverlauf zwischen dir und den Agenten sowie die Systemmeldungen.">Chat Verlauf</span>
        <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.08);"></div>
      </div>
      
      <!-- Bottom Pane: Normal Chat -->
      <div id="chat-display"></div>
    </div>
    
    <div class="chat-bar">
      <div class="chat-input-wrap" data-help-title="✍️ Chat-Eingabefeld" data-help="Tippe hier deine Fragen, Befehle oder Nachrichten ein. Nutze '@' für Agenten (z.B. @bs, @researcherag) und '@@' für Systemkommandos (z.B. @@status).">
        <div class="ac-dropdown" id="ac-dropdown"></div>
        <textarea id="chat-input" placeholder="@bs @research @idea …" oninput="onChatInput(this)" onkeydown="onChatKey(event)"></textarea>
      </div>
      <button class="btn-primary" onclick="sendChat()" style="padding:0 20px;" data-help-title="✉️ Chat absenden" data-help="Sende deine eingetippte Anweisung an den Schwarm ab, um die Bearbeitung zu starten.">Send</button>
      <input type="checkbox" id="tts-enabled" style="display:none;" ${ttsChecked ? 'checked' : ''}>
      
      <button id="tts-toggle-btn" class="btn-mic" onclick="toggleMainTTS()" title="Sprachausgabe (TTS)" style="padding:0 14px; margin-right: 6px; background: ${ttsChecked ? 'rgba(57,255,20,0.15)' : 'rgba(0,229,255,0.1)'}; border: 1px solid ${ttsChecked ? 'rgba(57,255,20,0.4)' : 'rgba(0,229,255,0.3)'}; color: ${ttsChecked ? 'var(--green)' : 'var(--cyan)'}; font-weight: bold;" data-help-title="🗣️ Sprachausgabe (TTS)" data-help="Schaltet das Vorlesen der Chat-Antworten ein oder aus. Der Vorleseton passt sich dem Charakter des jeweiligen Agenten an.">
        ${ttsChecked ? '🔊 TTS' : '🔇 TTS'}
      </button>
      
      <button id="stop-tts-btn" class="btn-mic btn-danger" onclick="stopTTS()" title="Sprachausgabe stoppen" style="padding:0 14px; margin-right: 6px; display:none; font-weight: bold; background: rgba(220, 20, 60, 0.2); border: 1px solid rgba(220, 20, 60, 0.4); color: var(--red);" data-help-title="🛑 Sprachausgabe stoppen" data-help="Stoppt das aktuelle Vorlesen sofort und löscht alle weiteren Nachrichten aus der Sprach-Warteschlange.">Stop</button>
      
      <button id="mic-btn" class="btn-mic" onclick="toggleSTT()" title="Voice Input" style="padding:0 14px; margin-right: 6px;" data-help-title="🎙️ Diktierfunktion (Rec)" data-help="Aktiviert die Spracheingabe über das Mikrofon. Sprich deine Befehle frei ein. Klicke erneut zum Beenden der Aufnahme.">Rec</button>
      
      <select id="chat-info-level-select" onchange="changeInfoLevel(this.value)" style="background: rgba(0,229,255,0.15); border: 1px solid rgba(0,229,255,0.3); color: var(--cyan); border-radius: 6px; padding: 0 10px; height: 38px; font-size: 0.75rem; cursor: pointer; outline: none; font-weight: bold; font-family: sans-serif; transition: all 0.2s; margin-left: 2px;" data-help-title="📊 Ansichts-Detailstufe" data-help="Passe die Detailtiefe der Agenten-Antworten und Logs an:<br><br>• <b>Detailliert:</b> Voller Denkprozess und ungekürzte Nachrichten.<br>• <b>Kompakt:</b> Zusammenfassung mit optionalem Aufklapp-Button.<br>• <b>Minimal:</b> Nur die allerwichtigsten Kerninfos, Denkfenster ausgeblendet.">
        <option value="detailed" ${window.infoLevel === 'detailed' ? 'selected' : ''}>🧠 Detailliert</option>
        <option value="compact" ${window.infoLevel === 'compact' ? 'selected' : ''}>💬 Kompakt</option>
        <option value="minimal" ${window.infoLevel === 'minimal' ? 'selected' : ''}>🔇 Minimal</option>
      </select>
    </div>
    ${buildChatHintsHTML()}
  </div>`;
}

function showWarRoom() {
  if (typeof trackView === 'function') trackView('war-room');
  selectedId = null;
  window._lastChatData = '';
  const searchInput = document.getElementById('agent-search');
  if (typeof renderAgentList === 'function') {
    renderAgentList(searchInput ? searchInput.value : '');
  }
  document.getElementById('content').innerHTML = buildWarRoomHTML();
  if (typeof changeInfoLevel === 'function') changeInfoLevel(window.infoLevel);
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
  dd.innerHTML = all.map(n => `<div class="ac-item" onmousedown="pickAc('${escapeHtml(n)}')">${BUILTIN_CMDS.includes(n) ? '@' + escapeHtml(n) : '@ ' + escapeHtml(n)}</div>`).join('');
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
  if (m === '@tts on') { const cb = document.getElementById('tts-enabled'); if (cb) { cb.checked = true; localStorage.setItem('ttsEnabled', 'true'); } ta.value = ''; toast('🗣️ TTS Aktiviert', 'success'); return true; }
  if (m === '@tts off') { const cb = document.getElementById('tts-enabled'); if (cb) { cb.checked = false; localStorage.setItem('ttsEnabled', 'false'); } stopTTS(); ta.value = ''; toast('🔇 TTS Deaktiviert', 'info'); return true; }
  if (m === '@tts') { const cb = document.getElementById('tts-enabled'); if (cb) { cb.checked = !cb.checked; localStorage.setItem('ttsEnabled', cb.checked ? 'true' : 'false'); if (!cb.checked) stopTTS(); toast(cb.checked ? '🗣️ TTS Aktiviert' : '🔇 TTS Deaktiviert', cb.checked ? 'success' : 'info'); } ta.value = ''; return true; }
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

function parseShowboxInMsg(m, overrideId) {
  let rawContent = "";
  let mid = "";
  if (m && typeof m === 'object') {
    rawContent = m.content || "";
    mid = m.id || Math.random().toString(36).slice(2);
  } else {
    rawContent = m || "";
    mid = overrideId || Math.random().toString(36).slice(2);
  }
  let showBoxFound = false;
  let showData = null;
  const showboxMatch = rawContent.match(/<SHOWBOX(?::(\d+))?>([\s\S]*?)<\/SHOWBOX>/);
  
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

function extractThoughtsAndClean(content) {
  const thoughts = [];
  const cleaned = content || "";
  const thinkRegex = /<think>([\s\S]*?)<\/think>/gi;
  let match;
  while ((match = thinkRegex.exec(cleaned)) !== null) {
    if (match[1].trim()) {
      thoughts.push(match[1].trim());
    }
  }
  const finalCleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  return { thoughts, cleaned: finalCleaned };
}

function cleanNormalChatMessage(safe) {
  // Replace WRITE actions
  safe = safe.replace(/\[WRITE:\s*([^\]\n]+)\]([\s\S]*?)\[\/WRITE\]/gi, function(match, filename, fileContent) {
    return `<div class="action-summary-badge write-badge">💾 <strong>Datei geschrieben:</strong> <code>${filename.trim()}</code></div>`;
  });
  // Replace SHELL actions
  safe = safe.replace(/\[SHELL:\s*([^\]\n]+)\]/gi, function(match, command) {
    return `<div class="action-summary-badge shell-badge">💻 <strong>Befehl ausgeführt:</strong> <code>${command.trim()}</code></div>`;
  });
  // Replace READ actions
  safe = safe.replace(/\[READ:\s*([^\]\n]+)\]/gi, function(match, filename) {
    return `<div class="action-summary-badge read-badge">📖 <strong>Datei gelesen:</strong> <code>${filename.trim()}</code></div>`;
  });
  // Replace BROWSER actions
  safe = safe.replace(/\[BROWSER:\s*([^\]\n]+)\]/gi, function(match, action) {
    return `<div class="action-summary-badge browser-badge">🌐 <strong>Browser-Aktion:</strong> <code>${action.trim()}</code></div>`;
  });
  // Replace IMAGE actions
  safe = safe.replace(/\[IMAGE:\s*([^\]\n]+)\]/gi, function(match, prompt) {
    return `<div class="action-summary-badge image-badge">🎨 <strong>Bild generiert:</strong> <code>${prompt.trim()}</code></div>`;
  });
  // Wrap code blocks
  safe = safe.replace(/```(\w*)\n([\s\S]*?)```/g, function(match, lang, code) {
    return `<details class="chat-code-block" style="margin: 8px 0; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; background: rgba(0,0,0,0.2);">
      <summary style="cursor: pointer; padding: 6px 10px; font-size: 0.72rem; color: var(--cyan); user-select: none; font-weight: 500;">💻 Code anzeigen (${lang || 'Text'})</summary>
      <pre style="margin: 0; padding: 10px; font-family: monospace; font-size: 0.75rem; border-top: 1px solid rgba(255,255,255,0.05); overflow-x: auto; white-space: pre-wrap; color: #a9b1d6; background: rgba(0,0,0,0.3);">${code.trim()}</pre>
    </details>`;
  });
  return safe;
}

window.thoughtTtsEnabled = true;
window.infoLevel = localStorage.getItem('infoLevel') || 'detailed';

function changeInfoLevel(level) {
  window.infoLevel = level;
  localStorage.setItem('infoLevel', level);
  
  // Synchronize both select dropdowns (header and chat bar)
  const headerSelect = document.getElementById('info-level-select');
  const chatSelect = document.getElementById('chat-info-level-select');
  if (headerSelect) headerSelect.value = level;
  if (chatSelect) chatSelect.value = level;
  
  const thoughtEl = document.getElementById('thought-display');
  const headerEl = document.querySelector('#chat-split-container > div:first-child');
  const splitterEl = document.querySelector('#chat-split-container > div:nth-child(3)');
  const splitContainer = document.getElementById('chat-split-container');
  const chatDisplay = document.getElementById('chat-display');

  if (thoughtEl && headerEl && splitterEl) {
    if (level === 'minimal') {
      thoughtEl.style.setProperty('display', 'none', 'important');
      headerEl.style.setProperty('display', 'none', 'important');
      splitterEl.style.setProperty('display', 'none', 'important');
      if (splitContainer) splitContainer.style.setProperty('height', 'auto', 'important');
      if (chatDisplay) {
        chatDisplay.style.setProperty('flex', 'none', 'important');
        chatDisplay.style.setProperty('height', '65vh', 'important');
      }
    } else {
      thoughtEl.style.setProperty('display', 'flex', 'important');
      headerEl.style.setProperty('display', 'flex', 'important');
      splitterEl.style.setProperty('display', 'flex', 'important');
      if (splitContainer) splitContainer.style.setProperty('height', '62vh', 'important');
      if (chatDisplay) {
        chatDisplay.style.setProperty('flex', '1.5', 'important');
        chatDisplay.style.setProperty('height', 'auto', 'important');
      }
    }
  }
  
  window._lastChatData = null;
  refreshChat();
}

function toggleMainTTS() {
  const cb = document.getElementById('tts-enabled');
  if (!cb) return;
  cb.checked = !cb.checked;
  localStorage.setItem('ttsEnabled', cb.checked ? 'true' : 'false');
  const btn = document.getElementById('tts-toggle-btn');
  if (btn) {
    if (cb.checked) {
      btn.innerHTML = '🔊 TTS';
      btn.style.background = 'rgba(57,255,20,0.15)';
      btn.style.borderColor = 'rgba(57,255,20,0.4)';
      btn.style.color = 'var(--green)';
      toast('🗣️ TTS Aktiviert', 'success');
    } else {
      btn.innerHTML = '🔇 TTS';
      btn.style.background = 'rgba(0,229,255,0.1)';
      btn.style.borderColor = 'rgba(0,229,255,0.3)';
      btn.style.color = 'var(--cyan)';
      stopTTS();
      toast('🔇 TTS Deaktiviert', 'info');
    }
  }
}

function toggleThoughtTTS() {
  window.thoughtTtsEnabled = !window.thoughtTtsEnabled;
  const btn = document.getElementById('thought-tts-btn');
  if (btn) {
    if (window.thoughtTtsEnabled) {
      btn.innerHTML = '🔊 TTS An';
      btn.style.background = 'rgba(57,255,20,0.15)';
      btn.style.borderColor = 'rgba(57,255,20,0.4)';
      btn.style.color = 'var(--green)';
      toast('🗣️ Denkprozess-TTS Aktiviert', 'success');
    } else {
      btn.innerHTML = '🔇 TTS Aus';
      btn.style.background = 'rgba(0,229,255,0.1)';
      btn.style.borderColor = 'rgba(0,229,255,0.3)';
      btn.style.color = 'var(--cyan)';
      stopTTS();
      toast('🔇 Denkprozess-TTS Deaktiviert', 'info');
    }
  }
}

function renderThoughtMessageHTML(sender, content, timestamp) {
  const c = agentColor(sender);
  const time = timestamp ? new Date(timestamp).toLocaleTimeString() : '';
  
  let displayContent = content;
  if (window.infoLevel === 'compact') {
    const lines = content.split('\n');
    if (lines.length > 2 || content.length > 120) {
      displayContent = lines.slice(0, 2).join('\n').substring(0, 120).trim() + ' ... (Gedanken komprimiert)';
    }
  }
  
  const safeContent = esc(displayContent).replace(/\n/g, '<br>');
  return `<div class="thought-msg" style="border-left: 3px solid ${c}; background: rgba(0, 229, 255, 0.015); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: var(--radius-sm); padding: 8px 10px; margin-bottom: 6px;">
    <div style="display: flex; justify-content: space-between; font-size: 0.65rem; color: var(--text-muted); margin-bottom: 4px;">
      <span><strong style="color: ${c}">${esc(sender)}</strong> <span style="background: rgba(0, 229, 255, 0.12); color: var(--cyan); padding: 1px 5px; border-radius: 4px; font-size: 0.55rem; font-weight: bold; margin-left: 4px; letter-spacing: 0.3px;">THINKING</span></span>
      <span>${time}</span>
    </div>
    <div style="font-size: 0.72rem; line-height: 1.35; color: rgba(255,255,255,0.7); font-family: monospace; white-space: pre-wrap; word-break: break-word;">${safeContent}</div>
  </div>`;
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

function renderChatMessageHTML(m, overrideContent) {
  const isUser = m.metadata?.sender === 'user' || m.sender?.toLowerCase() === 'user';
  const name = isUser ? 'You' : (m.metadata?.sender || m.sender || 'System');
  const time = m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : '';
  const c = isUser ? 'var(--primary)' : agentColor(name);
  const nameColor = isUser ? 'var(--primary)' : (name.toLowerCase().startsWith('testag') ? '#0066FF' : 'inherit');
  const mid = m.id || Math.random().toString(36).slice(2);
  
  const contentToUse = overrideContent !== undefined ? overrideContent : (m.content || "");
  const { rawContent, showBoxFound, showData } = parseShowboxInMsg(contentToUse, mid);
  let safe = esc(rawContent);
  
  if (showBoxFound && showData) {
    let slides = showData;
    if (showData && !Array.isArray(showData) && Array.isArray(showData.slides)) {
      slides = showData.slides;
    }
    if (slides && Array.isArray(slides) && slides.length > 0) {
      if (document.body.classList.contains('supergnom-mode')) {
        safe += `
          <div class="inline-showbox-container" style="margin-top: 12px; border: 1px solid var(--glass-border); border-radius: var(--radius); background: rgba(16, 20, 32, 0.4); padding: 15px; overflow: hidden; backdrop-filter: blur(8px);">
            <div style="font-size: 0.72rem; color: var(--cyan); text-transform: uppercase; font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
              🖥️ Visuelle Ausgabe / Entwurf
            </div>
            <div class="inline-showbox-body" style="font-size: 0.85rem; color: #fff; max-height: 400px; overflow-y: auto;">
              ${slides[0]}
            </div>
          </div>
        `;
      } else {
        const targetText = (showData && showData._targetIdx !== undefined) ? ` Button ${showData._targetIdx + 1}` : '';
        safe += `<div style="color:var(--cyan);font-size:0.8em;margin-top:8px;">[ 🎬 Showbox Triggered${targetText} ]</div>`;
      }
    }
  } else if (showBoxFound) {
    const targetText = (showData && showData._targetIdx !== undefined) ? ` Button ${showData._targetIdx + 1}` : '';
    safe += `<div style="color:var(--cyan);font-size:0.8em;margin-top:8px;">[ 🎬 Showbox Triggered${targetText} ]</div>`;
  }
  
  handleShowboxTrigger(showData, name);

  safe = cleanNormalChatMessage(safe);
  
  if ((window.infoLevel === 'compact' || window.infoLevel === 'minimal') && !isUser && rawContent.length > 150) {
    const brief = rawContent.substring(0, 150).trim();
    const fullEsc = esc(rawContent).replace(/\n/g, '<br>');
    safe = `<div class="compact-view-wrapper">
        <span class="brief-text" style="color: rgba(255,255,255,0.85);">${esc(brief)}...</span>
        <details style="display: inline; cursor: pointer; outline: none;">
          <summary style="font-size: 0.65rem; color: var(--cyan); display: inline-block; padding: 2.5px 7px; border: 1px solid rgba(0, 229, 255, 0.25); border-radius: 4px; margin-left: 6px; font-weight: bold; font-family: sans-serif; user-select: none;">Mehr anzeigen</summary>
          <div style="margin-top: 10px; padding: 10px; border-left: 2px solid var(--cyan); background: rgba(0,229,255,0.02); color: rgba(255,255,255,0.9); font-size: 0.76rem; line-height: 1.45; border-radius: 4px; font-family: monospace;">
            ${fullEsc}
          </div>
        </details>
      </div>`;
  } else {
    safe = safe.replace(/\[SOUL:\s*([\s\S]*?)\]/g, '<div style="font-size:0.6rem; color:var(--bg-surface); opacity:0.5; margin-top:4px;">[SOUL: $1]</div>');
    safe = safe.replace(/\n/g, '<br>');
  }

  // Collapsible Thoughts for SuperGNOM Mode
  let thoughtsHTML = "";
  const { thoughts } = extractThoughtsAndClean(m.content || "");
  if (document.body.classList.contains('supergnom-mode') && !isUser && thoughts && thoughts.length > 0) {
    thoughtsHTML = `
      <details class="agent-thoughts-block" style="margin-bottom: 12px; border: 1px solid rgba(0, 229, 255, 0.15); border-radius: var(--radius-sm); background: rgba(0, 229, 255, 0.02); overflow: hidden;">
        <summary style="cursor: pointer; padding: 6px 12px; font-size: 0.72rem; color: var(--cyan); font-weight: 600; list-style: none; display: flex; align-items: center; gap: 6px; user-select: none;">
          <span class="thoughts-arrow" style="transition: transform 0.2s; display: inline-block;">▶</span> 🧠 Denkprozess anzeigen
        </summary>
        <div style="padding: 10px 12px; font-size: 0.72rem; line-height: 1.45; color: rgba(255, 255, 255, 0.75); border-top: 1px solid rgba(0, 229, 255, 0.08); font-family: monospace; white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow-y: auto;">
          ${thoughts.map(t => esc(t)).join('<br><br>')}
        </div>
      </details>
    `;
  }

  return `<div class="chat-msg ${isUser ? 'user' : 'agent'}" style="border-left-color:${c};">
    <div class="chat-meta"><span class="agent-name" style="color:${nameColor}">${esc(name)}</span><span><button class="copy-btn" onclick="copyMsg('${mid}')" title="Copy">📋</button><button class="copy-btn del-btn" onclick="deleteChatMsg('${mid}')" title="Delete">🗑</button>${time}</span></div>
    ${thoughtsHTML}
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

  const thoughtEl = document.getElementById('thought-display');
  const thoughtSt = thoughtEl ? thoughtEl.scrollTop : 0;
  const thoughtWasAtBottom = thoughtEl ? (thoughtEl.scrollHeight - thoughtEl.scrollTop - thoughtEl.clientHeight < 60) : false;

  if (!msgs || !msgs.length) { 
    el.innerHTML = '<div class="empty">No messages yet.</div>'; 
    if (thoughtEl) thoughtEl.innerHTML = '<div class="empty" style="padding:10px; font-size:0.7rem;">Keine Denkprozesse aktiv.</div>';
    return; 
  }
  
  const sorted = msgs.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
  window._processedShowboxes = window._processedShowboxes || new Set();

  if (!window._spokenIds) window._spokenIds = new Set();
  if (!window._spokenThoughtIds) window._spokenThoughtIds = new Set();

  let chatHTML = "";
  let thoughtHTML = "";

  for (const m of sorted) {
    const isUser = m.metadata?.sender === 'user' || m.sender?.toLowerCase() === 'user';
    const sender = isUser ? 'You' : (m.metadata?.sender || m.sender || 'System');
    const timestamp = m.timestamp;
    
    // 1. Extract thoughts
    const { thoughts, cleaned } = extractThoughtsAndClean(m.content);
    
    if (thoughts.length > 0) {
      for (let i = 0; i < thoughts.length; i++) {
        const thought = thoughts[i];
        const thoughtId = m.id + "-" + i;
        
        // Render thought entry
        thoughtHTML += renderThoughtMessageHTML(sender, thought, timestamp);
        
        // Speak thought if new and main TTS is enabled, and view is not minimal
        if (!window._spokenThoughtIds.has(thoughtId)) {
          const ttsChecked = localStorage.getItem('ttsEnabled') !== 'false';
          if (ttsChecked && window.infoLevel !== 'minimal') {
            let speakThought = thought;
            if (window.infoLevel === 'compact') {
              speakThought = thought.split(/[.!?]/)[0].trim() + ".";
            }
            speak(`${sender} denkt: ${speakThought}`, sender);
          }
          window._spokenThoughtIds.add(thoughtId);
        }
      }
    }
    
    // 2. Render normal chat
    chatHTML += renderChatMessageHTML(m, cleaned);
    
    // 3. Speak normal message if new and main TTS is enabled
    if (!isUser && !window._spokenIds.has(m.id)) {
      window._spokenIds.add(m.id);
      let speechText = cleaned.replace(/\[WRITE:\s*([^\]\n]+)\]([\s\S]*?)\[\/WRITE\]/gi, 'schreibt Datei $1')
                              .replace(/\[SHELL:\s*([^\]\n]+)\]/gi, 'führt Befehl $1 aus')
                              .replace(/<SHOWBOX[\s\S]*?<\/SHOWBOX>/gi, '')
                              .trim();
      const hasBlock = cleaned.includes('blockiert') || cleaned.includes('BLOCKIERT') || 
                       cleaned.includes('Fehler') || cleaned.includes('permission denied') || 
                       cleaned.includes('keine WRITE') || cleaned.includes('keine SHELL') ||
                       cleaned.includes('Gatekeeper') || cleaned.includes('System-Blockade');
      if (hasBlock) {
        speechText = "🛑 CRITICAL: System-Blockade";
      }
      if (speechText) {
        if (speechText === "🛑 CRITICAL: System-Blockade") {
          speak(speechText, sender);
        } else {
          if (window.infoLevel === 'compact' || window.infoLevel === 'minimal') {
            speechText = speechText.split(/[.!?]/)[0].trim() + ".";
          }
          speak(`${sender} sagt: ${speechText}`, sender);
        }
      }
    }
  }

  el.innerHTML = chatHTML || '<div class="empty">No messages yet.</div>';

  if (wasAtBottom || !window._chatInitialized) {
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    window._chatInitialized = true;
  } else {
    el.scrollTop = st;
  }

  if (thoughtEl) {
    thoughtEl.innerHTML = thoughtHTML || '<div class="empty" style="padding:10px; font-size:0.7rem;">Keine Denkprozesse aktiv.</div>';
    if (thoughtWasAtBottom || !window._thoughtInitialized) {
      thoughtEl.scrollTo({ top: thoughtEl.scrollHeight, behavior: 'smooth' });
      window._thoughtInitialized = true;
    } else {
      thoughtEl.scrollTop = thoughtSt;
    }
  }
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
  if (!filtered.length) return null;
  
  // Prioritize premium/high-quality voices, but EXCLUDE Siri which fails to play on Webkit/Safari on macOS
  const premium = filtered.filter(v => 
    (v.name.includes('Premium') || 
     v.name.includes('Enhanced') || 
     v.name.includes('Google') || 
     v.name.includes('Yannick') || 
     v.name.includes('Anna')) &&
    !v.name.includes('Siri')
  );
  if (premium.length > 0) {
    filtered = premium;
  }
  
  let hash = 0;
  for (let i = 0; i < agentName.length; i++) {
    hash = agentName.charCodeAt(i) + ((hash << 5) - hash);
  }
  return filtered[Math.abs(hash) % filtered.length];
}

async function speak(text, agentId = '') {
  if (localStorage.getItem('ttsEnabled') === 'false') return;
  _ttsQ.push({ text, agentId });
  if (_ttsBusy) return;
  _ttsBusy = true;
  const stopBtn = document.getElementById('stop-tts-btn');
  if (stopBtn) stopBtn.style.display = 'block';

  while (_ttsQ.length) {
    const { text: t, agentId: a } = _ttsQ.shift();
    if (typeof speechSynthesis !== 'undefined') {
      speechSynthesis.cancel();
    }
    
    let elevenLabsSuccess = false;
    if (window.hasElevenLabs) {
      try {
        const r = await fetch(`${API}/audio/tts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: t, agent_id: a }) });
        if (r.ok && r.headers.get('content-type')?.includes('audio')) {
          const audio = new Audio(URL.createObjectURL(await r.blob()));
          await new Promise(ok => {
            let resolved = false;
            const done = () => {
              if (!resolved) {
                resolved = true;
                clearTimeout(timeoutId);
                ok();
              }
            };
            audio.onended = done;
            audio.onerror = done;
            const timeoutId = setTimeout(done, 15000); // 15 seconds safety timeout
            audio.play().catch(err => {
              console.error("ElevenLabs audio play failed:", err);
              done();
            });
          });
          elevenLabsSuccess = true;
        }
      } catch (e) {
        console.warn("ElevenLabs TTS failed, falling back to browser synthesis:", e);
      }
    }
    
    if (elevenLabsSuccess) continue;
    
    if (typeof speechSynthesis === 'undefined') continue;
    
    const u = new SpeechSynthesisUtterance(t);
    u.lang = 'de-DE';
    u.rate = 1.0;
    const voice = getVoiceForAgent(a || 'System', u.lang);
    if (voice) u.voice = voice;
    
    // Resume to prevent Chrome/Safari speech from staying paused
    speechSynthesis.resume();
    
    await new Promise(ok => {
      let resolved = false;
      const done = () => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeoutId);
          ok();
        }
      };
      u.onend = done;
      u.onerror = done;
      
      // Safety timeout: 100ms per character, minimum 5 seconds, maximum 20 seconds
      const duration = Math.min(20000, Math.max(5000, t.length * 100));
      const timeoutId = setTimeout(() => {
        console.warn("Browser SpeechSynthesis timeout exceeded, cancelling");
        try {
          speechSynthesis.cancel();
        } catch {}
        done();
      }, duration);
      
      try {
        speechSynthesis.speak(u);
      } catch (err) {
        console.error("SpeechSynthesis.speak failed:", err);
        done();
      }
    });
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
    expl.innerHTML = `🛡️ <strong>Project Mode active: ${escapeHtml(p)}</strong><br>You are in project <b>${escapeHtml(p)}</b>. Communications, files, and agent thoughts are saved exclusively for this project. If you return in 10 years, you will find everything exactly as you left it. <i>(Type <code>@project default</code> to exit the project)</i>`;
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

// Unlocks Browser SpeechSynthesis on first user click
window.addEventListener('click', () => {
  if (typeof speechSynthesis !== 'undefined' && !window._speechSynthesisUnlocked) {
    try {
      const u = new SpeechSynthesisUtterance('');
      speechSynthesis.speak(u);
      window._speechSynthesisUnlocked = true;
      console.log("SpeechSynthesis unlocked successfully via click interaction");
    } catch (e) {
      console.warn("Failed to unlock SpeechSynthesis:", e);
    }
  }
}, { once: true });

