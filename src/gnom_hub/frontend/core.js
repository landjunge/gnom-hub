/* ═══════════════════════════════════════════
   GNOM-HUB — Core Logic & Shared State
   ═══════════════════════════════════════════ */

// Shared Globals
var API = '';
var agents = [];
window.agents = agents;
var selectedId = null;
var _intervalIds = [];

// Navigation History
window.viewHistory = [];
window.currentView = 'war-room';

var _nukeTimer = null;
var _nukeArmed = false;
var _nukeAudioCtx = null;

const P_COLORS = ['#00E5FF', '#B026FF', '#FF007F', '#39FF14', '#FF3366', '#8A2BE2', '#0066FF', '#00FF9D', '#FF9900', '#FFD700', '#FF1493', '#00FA9A', '#1E90FF', '#FF4500', '#00FFFF'];
const KNOWN_COLORS = {
  'soulag': '#FF5E00',
  'generalag': '#00FFFF',
  'securityag': '#FF69B4',
  'watchdogag': '#FFA500',
  'researcherag': '#FFFF00',
  'writerag': '#00FF00',
  'editorag': '#0088FF',
  'coderag': '#FF0000'
};


// ── Toast ──
function toast(msg, type = 'info') {
  if (typeof window.showboxToast === 'function') {
    window.showboxToast(msg, type);
  } else {
    const c = document.getElementById('toasts');
    if (c) {
      const t = document.createElement('div');
      t.className = `toast ${type}`;
      t.textContent = msg;
      c.appendChild(t);
      setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 300); }, 10500);
    }
  }
}

async function cleanAll() {
  if (!confirm('⚠️ Datenbanken zurücksetzen?\n\nEs wird ZUERST ein Backup aller Datenbanken erstellt.\n\nDB-Inhalt: Chat, Tokens, Soul-Memory, Workflows — alles weg!\n\nWICHTIG: Dein Workspace (~gnom-Workspace/) bleibt UNVERÄNDERT.\nHub startet danach neu.')) return;
  toast('💾 Erstelle Backup vor dem Cleanup…', 'info');
  const r = await api('POST', '/admin/clean-all');
  if (r && r.status === 'cleaned') {
    const bp = r.backup && r.backup.path ? r.backup.path : '(unbekannt)';
    toast('✅ Backup: ' + bp + ' — Hub startet neu…', 'success');
    setTimeout(() => location.reload(), 3000);
  } else if (r && r.status === 'aborted') {
    toast('🛑 ABGEBROCHEN: ' + (r.reason || 'Backup fehlgeschlagen') + ' — Daten NICHT gelöscht.', 'error');
  } else {
    toast('Fehler beim Cleanup', 'error');
  }
}

// ── NUKE (G-Button Long Press & Retro TV Effect) ──
function nukeStart(e) {
  e.stopPropagation();
  try {
    if (!_nukeAudioCtx) {
      _nukeAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (_nukeAudioCtx.state === 'suspended') {
      _nukeAudioCtx.resume();
    }
  } catch (err) {
    console.warn("AudioContext failed to initialize:", err);
  }

  const btn = document.getElementById('nuke-btn');
  btn.classList.add('nuke-charging');
  _nukeArmed = false;
  _nukeTimer = setTimeout(() => {
    _nukeArmed = true;
    btn.classList.remove('nuke-charging');
    btn.classList.add('nuke-fired');
    nukeHub();
  }, 2000);
}

function nukeCancel() {
  if (_nukeTimer) { clearTimeout(_nukeTimer); _nukeTimer = null; }
  if (!_nukeArmed) {
    const btn = document.getElementById('nuke-btn');
    btn.classList.remove('nuke-charging');
  }
}

async function nukeHub() {
  const btn = document.getElementById('nuke-btn');
  try {
    fetch((API || '/api').replace('/api', '') + '/api/admin/nuke', { method: 'POST' }).catch(() => {});
  } catch (err) {}

  btn.textContent = '✕';
  btn.classList.remove('nuke-fired');
  btn.classList.add('nuke-offline');

  if (!document.getElementById('nuke-styles')) {
    const style = document.createElement('style');
    style.id = 'nuke-styles';
    style.textContent = `
      @keyframes nuke-blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
      }
      .nuke-overlay {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: 999999;
        background: #000;
        overflow: hidden;
        user-select: none;
        pointer-events: all;
      }
      .nuke-overlay.white-flash {
        background: #fff !important;
      }
      .crt-effect::after {
        content: " ";
        display: block;
        position: absolute;
        top: 0; left: 0; bottom: 0; right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%),
                    linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        z-index: 99999999;
        background-size: 100% 4px, 6px 100%;
        pointer-events: none;
      }
      .crt-effect {
        animation: crt-flicker 0.15s infinite;
      }
      @keyframes crt-flicker {
        0% { opacity: 0.985; }
        50% { opacity: 1.0; }
        100% { opacity: 0.99; }
      }
      @keyframes nuke-shake {
        0% { transform: translate(0, 0) rotate(0deg); }
        10% { transform: translate(-3px, 2px) rotate(-1deg); }
        20% { transform: translate(3px, -2px) rotate(1deg); }
        30% { transform: translate(-2px, -3px) rotate(0deg); }
        40% { transform: translate(2px, 3px) rotate(1deg); }
        50% { transform: translate(-3px, 1px) rotate(-1deg); }
        60% { transform: translate(3px, 2px) rotate(0deg); }
        70% { transform: translate(-1px, -2px) rotate(1deg); }
        80% { transform: translate(2px, -1px) rotate(-1deg); }
        90% { transform: translate(-2px, 3px) rotate(0deg); }
        100% { transform: translate(0, 0) rotate(0deg); }
      }
      .nuke-shake {
        animation: nuke-shake 0.15s infinite;
      }
    `;
    document.head.appendChild(style);
  }

  const overlay = document.createElement('div');
  overlay.className = 'nuke-overlay white-flash';
  document.body.appendChild(overlay);

  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'width:100%;height:100%;display:block;';
  overlay.appendChild(canvas);

  const terminal = document.createElement('div');
  terminal.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%;padding:40px;box-sizing:border-box;color:#39ff14;font-family:'Courier New',Courier,monospace;font-size:18px;line-height:1.6;text-shadow:0 0 5px #39ff14;display:none;flex-direction:column;justify-content:flex-start;overflow-y:auto;background:transparent;";
  
  const termContent = document.createElement('div');
  terminal.appendChild(termContent);
  
  const cursor = document.createElement('span');
  cursor.style.cssText = 'display:inline-block;width:10px;height:18px;background:#39ff14;margin-left:2px;vertical-align:middle;animation:nuke-blink 1s infinite;';
  terminal.appendChild(cursor);
  overlay.appendChild(terminal);

  let noiseSource = null;
  let humOsc = null;
  let noiseGain = null;
  let humGain = null;

  function startAudio() {
    if (!_nukeAudioCtx) return;
    try {
      const bufferSize = _nukeAudioCtx.sampleRate * 2;
      const buffer = _nukeAudioCtx.createBuffer(1, bufferSize, _nukeAudioCtx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
      }
      noiseSource = _nukeAudioCtx.createBufferSource();
      noiseSource.buffer = buffer;
      noiseSource.loop = true;

      noiseGain = _nukeAudioCtx.createGain();
      noiseGain.gain.setValueAtTime(0.12, _nukeAudioCtx.currentTime);
      noiseSource.connect(noiseGain);
      noiseGain.connect(_nukeAudioCtx.destination);

      humOsc = _nukeAudioCtx.createOscillator();
      humOsc.type = 'sine';
      humOsc.frequency.setValueAtTime(55, _nukeAudioCtx.currentTime);
      humGain = _nukeAudioCtx.createGain();
      humGain.gain.setValueAtTime(0.08, _nukeAudioCtx.currentTime);
      humOsc.connect(humGain);
      humGain.connect(_nukeAudioCtx.destination);

      noiseSource.start();
      humOsc.start();
    } catch (err) {
      console.warn("Could not play nuke sound effects:", err);
    }
  }

  function stopAudioAndPlayClick() {
    if (!_nukeAudioCtx) return;
    try {
      const now = _nukeAudioCtx.currentTime;
      if (noiseGain) noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
      if (humGain) humGain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
      setTimeout(() => {
        try { if (noiseSource) noiseSource.stop(); } catch(e){}
        try { if (humOsc) humOsc.stop(); } catch(e){}
      }, 150);

      const clickOsc = _nukeAudioCtx.createOscillator();
      clickOsc.type = 'sine';
      clickOsc.frequency.setValueAtTime(160, now);
      clickOsc.frequency.exponentialRampToValueAtTime(10, now + 0.1);
      const clickGain = _nukeAudioCtx.createGain();
      clickGain.gain.setValueAtTime(0.4, now);
      clickGain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
      clickOsc.connect(clickGain);
      clickGain.connect(_nukeAudioCtx.destination);
      clickOsc.start();
      clickOsc.stop(now + 0.12);

      const whineOsc = _nukeAudioCtx.createOscillator();
      whineOsc.type = 'sine';
      whineOsc.frequency.setValueAtTime(9000, now);
      const whineGain = _nukeAudioCtx.createGain();
      whineGain.gain.setValueAtTime(0.04, now);
      whineGain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      whineOsc.connect(whineGain);
      whineGain.connect(_nukeAudioCtx.destination);
      whineOsc.start();
      whineOsc.stop(now + 0.36);
    } catch (err) {
      console.warn("Could not play implosion sound:", err);
    }
  }

  function playGodzillaRoar(audioCtx) {
    if (!audioCtx) return;
    try {
      const now = audioCtx.currentTime;
      const mainGain = audioCtx.createGain();
      mainGain.gain.setValueAtTime(0.001, now);
      mainGain.gain.linearRampToValueAtTime(0.65, now + 0.15);
      mainGain.gain.exponentialRampToValueAtTime(0.5, now + 1.2);
      mainGain.gain.exponentialRampToValueAtTime(0.001, now + 2.4);
      mainGain.connect(audioCtx.destination);

      const tremoloOsc = audioCtx.createOscillator();
      tremoloOsc.frequency.setValueAtTime(13, now);
      const tremoloGain = audioCtx.createGain();
      tremoloGain.gain.setValueAtTime(0.45, now);
      tremoloOsc.connect(tremoloGain);

      const tremoloNode = audioCtx.createGain();
      tremoloNode.gain.setValueAtTime(0.55, now);
      tremoloGain.connect(tremoloNode.gain);
      tremoloNode.connect(mainGain);
      tremoloOsc.start(now);
      tremoloOsc.stop(now + 2.5);

      const distortion = audioCtx.createWaveShaper();
      function makeDistortionCurve(amount) {
        const k = amount;
        const n_samples = 44100;
        const curve = new Float32Array(n_samples);
        const deg = Math.PI / 180;
        for (let i = 0; i < n_samples; ++i) {
          const x = (i * 2) / n_samples - 1;
          curve[i] = ((3 + k) * x * 20 * deg) / (Math.PI + k * Math.abs(x));
        }
        return curve;
      }
      distortion.curve = makeDistortionCurve(80);
      distortion.oversample = '4x';
      distortion.connect(tremoloNode);

      const oscScreech = audioCtx.createOscillator();
      oscScreech.type = 'sawtooth';
      oscScreech.frequency.setValueAtTime(390, now);
      oscScreech.frequency.linearRampToValueAtTime(700, now + 0.15);
      oscScreech.frequency.exponentialRampToValueAtTime(250, now + 1.2);
      oscScreech.frequency.exponentialRampToValueAtTime(90, now + 2.4);

      const filterScreech = audioCtx.createBiquadFilter();
      filterScreech.type = 'bandpass';
      filterScreech.Q.setValueAtTime(4.5, now);
      filterScreech.frequency.setValueAtTime(900, now);
      filterScreech.frequency.exponentialRampToValueAtTime(1400, now + 0.15);
      filterScreech.frequency.exponentialRampToValueAtTime(450, now + 1.2);
      filterScreech.frequency.exponentialRampToValueAtTime(180, now + 2.4);

      const rattleLFO = audioCtx.createOscillator();
      rattleLFO.type = 'sawtooth';
      rattleLFO.frequency.setValueAtTime(48, now);
      const rattleGain = audioCtx.createGain();
      rattleGain.gain.setValueAtTime(160, now);
      rattleLFO.connect(rattleGain);
      rattleGain.connect(filterScreech.frequency);
      rattleLFO.start(now);
      rattleLFO.stop(now + 2.5);

      const gainScreech = audioCtx.createGain();
      gainScreech.gain.setValueAtTime(0.65, now);

      oscScreech.connect(filterScreech);
      filterScreech.connect(gainScreech);
      gainScreech.connect(distortion);
      oscScreech.start(now);
      oscScreech.stop(now + 2.5);

      const oscGrowl = audioCtx.createOscillator();
      oscGrowl.type = 'sawtooth';
      oscGrowl.frequency.setValueAtTime(80, now);
      oscGrowl.frequency.linearRampToValueAtTime(120, now + 0.2);
      oscGrowl.frequency.exponentialRampToValueAtTime(55, now + 1.2);
      oscGrowl.frequency.exponentialRampToValueAtTime(25, now + 2.4);

      const filterGrowl = audioCtx.createBiquadFilter();
      filterGrowl.type = 'lowpass';
      filterGrowl.Q.setValueAtTime(6, now);
      filterGrowl.frequency.setValueAtTime(280, now);
      filterGrowl.frequency.exponentialRampToValueAtTime(120, now + 1.5);

      const growlLFO = audioCtx.createOscillator();
      growlLFO.type = 'sawtooth';
      growlLFO.frequency.setValueAtTime(35, now);
      const growlGain = audioCtx.createGain();
      growlGain.gain.setValueAtTime(20, now);
      growlLFO.connect(growlGain);
      growlGain.connect(oscGrowl.frequency);
      growlLFO.start(now);
      growlLFO.stop(now + 2.5);

      const gainGrowl = audioCtx.createGain();
      gainGrowl.gain.setValueAtTime(0.75, now);

      oscGrowl.connect(filterGrowl);
      filterGrowl.connect(gainGrowl);
      gainGrowl.connect(distortion);
      oscGrowl.start(now);
      oscGrowl.stop(now + 2.5);

      const bufferSize = audioCtx.sampleRate * 2.5;
      const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
      }
      const noise = audioCtx.createBufferSource();
      noise.buffer = buffer;

      const noiseFilter = audioCtx.createBiquadFilter();
      noiseFilter.type = 'bandpass';
      noiseFilter.Q.setValueAtTime(2, now);
      noiseFilter.frequency.setValueAtTime(450, now);
      noiseFilter.frequency.exponentialRampToValueAtTime(180, now + 1.8);

      const noiseGainNode = audioCtx.createGain();
      noiseGainNode.gain.setValueAtTime(0.12, now);
      noiseGainNode.gain.exponentialRampToValueAtTime(0.001, now + 2.4);

      noise.connect(noiseFilter);
      noiseFilter.connect(noiseGainNode);
      noiseGainNode.connect(distortion);
      noise.start(now);
      noise.stop(now + 2.5);
    } catch (err) {
      console.warn("Godzilla roar sound synthesis failed:", err);
    }
  }

  const ctx = canvas.getContext('2d');
  let animFrameId = null;

  function resizeCanvas() {
    canvas.width = Math.max(100, window.innerWidth / 2);
    canvas.height = Math.max(100, window.innerHeight / 2);
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function drawStatic() {
    const w = canvas.width;
    const h = canvas.height;
    const imgData = ctx.createImageData(w, h);
    const data = imgData.data;
    const len = data.length;
    for (let i = 0; i < len; i += 4) {
      const val = Math.random() > 0.5 ? 255 : 0;
      data[i] = val;
      data[i+1] = val;
      data[i+2] = val;
      data[i+3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);
    animFrameId = requestAnimationFrame(drawStatic);
  }

  setTimeout(() => {
    overlay.classList.remove('white-flash');
    overlay.classList.add('crt-effect');
    startAudio();
    drawStatic();

    setTimeout(() => {
      cancelAnimationFrame(animFrameId);
      stopAudioAndPlayClick();

      const startImplode = performance.now();
      const durationVert = 200;
      const durationHoriz = 150;

      function animateImplosion(now) {
        const elapsed = now - startImplode;
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#fff';
        if (elapsed < durationVert) {
          const pct = elapsed / durationVert;
          const h = canvas.height * (1 - pct);
          const y = (canvas.height - h) / 2;
          ctx.fillRect(0, y, canvas.width, Math.max(2, h));
          animFrameId = requestAnimationFrame(animateImplosion);
        } else if (elapsed < (durationVert + durationHoriz)) {
          const pct = (elapsed - durationVert) / durationHoriz;
          const w = canvas.width * (1 - pct);
          const x = (canvas.width - w) / 2;
          ctx.fillRect(x, (canvas.height - 2) / 2, Math.max(2, w), 2);
          animFrameId = requestAnimationFrame(animateImplosion);
        } else {
          canvas.style.display = 'none';
          window.removeEventListener('resize', resizeCanvas);
          terminal.style.display = 'flex';
          setTimeout(startTerminalBoot, 2000);
        }
      }
      animFrameId = requestAnimationFrame(animateImplosion);
    }, 800);
  }, 10);

  function typeText(element, text, speed = 25) {
    return new Promise((resolve) => {
      let i = 0;
      function type() {
        if (i < text.length) {
          element.textContent += text.charAt(i);
          i++;
          setTimeout(type, speed);
        } else {
          resolve();
        }
      }
      type();
    });
  }

  async function startTerminalBoot() {
    const addLine = () => {
      const d = document.createElement('div');
      termContent.appendChild(d);
      terminal.scrollTop = terminal.scrollHeight;
      return d;
    };

    let line = addLine();
    await typeText(line, "system KILL ALL Processssssesss...", 5);
    await new Promise(r => setTimeout(r, 200));
    line.textContent += " [OK]";

    line = addLine();
    await typeText(line, "PURGING AGENT TEMPORARY CONTEXTS...", 5);
    await new Promise(r => setTimeout(r, 60));
    line.textContent += " [OK]";

    line = addLine();
    await typeText(line, "KILLING ORPHANED DOCKER DAEMONS...", 5);
    await new Promise(r => setTimeout(r, 40));
    line.textContent += " [OK]";

    line = addLine();
    await typeText(line, "REBOOTING LOCAL WORKSPACE NODE...", 5);
    await new Promise(r => setTimeout(r, 80));
    line.textContent += " [OK]";

    line = addLine();
    await typeText(line, "CONNECTING TO BROADCAST CONTROLLER...", 5);

    let sec = 0;
    let dotCount = 0;
    while (true) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 250);
        const r = await fetch((API || '/api').replace('/api', '') + '/api/health', { signal: controller.signal });
        clearTimeout(timeoutId);
        if (r.ok) {
          line.textContent += " [SUCCESS]";
          
          line = addLine();
          await typeText(line, "RE-INITIALIZING GNOM-HUB INTERFACE...", 5);
          await new Promise(r => setTimeout(r, 40));
          
          line = addLine();
          line.style.color = '#39ff14';
          line.style.fontSize = '24px';
          line.style.fontWeight = 'bold';
          line.style.marginTop = '15px';
          await typeText(line, "SYSTEM READY", 5);
          await new Promise(r => setTimeout(r, 300));

          termContent.innerHTML = '';
          
          line = addLine();
          line.style.color = '#39ff14';
          line.style.fontSize = '18px';
          line.style.fontFamily = 'Courier New, monospace';
          await typeText(line, "Wake up, gnom-hub...", 40);
          await new Promise(r => setTimeout(r, 800));
          
          line = addLine();
          line.style.color = '#39ff14';
          line.style.fontSize = '18px';
          line.style.fontFamily = 'Courier New, monospace';
          await typeText(line, "The Matrix has you...", 40);
          await new Promise(r => setTimeout(r, 800));
          
          line = addLine();
          line.style.color = '#39ff14';
          line.style.fontSize = '18px';
          line.style.fontFamily = 'Courier New, monospace';
          await typeText(line, "Follow the white rabbit.", 40);
          await new Promise(r => setTimeout(r, 1000));
          
          line = addLine();
          line.style.color = '#39ff14';
          line.style.fontSize = '18px';
          line.style.fontFamily = 'Courier New, monospace';
          await typeText(line, "Knock, knock, gnom-hub.", 40);

          playGodzillaRoar(_nukeAudioCtx);
          overlay.classList.add('nuke-shake');

          btn.textContent = 'G';
          btn.classList.remove('nuke-offline');
          btn.classList.add('nuke-ready');
          _nukeArmed = false;

          await new Promise(r => setTimeout(r, 3500));
          overlay.remove();
          location.reload();
          break;
        }
      } catch(e) {}

      line.textContent += ".";
      dotCount++;
      if (dotCount > 15) {
        line = addLine();
        line.textContent = "RETRACTING CONTROLLER PING LINK...";
        dotCount = 0;
      }

      sec += 0.3;
      if (sec > 60) {
        const lineErr = addLine();
        lineErr.style.color = '#ff3333';
        await typeText(lineErr, "TIMEOUT: SERVER FAILED TO RESPOND IN 60S.", 10);
        const lineTip = addLine();
        await typeText(lineTip, "PLEASE RUN MANUALLY: python3 -m gnom_hub", 10);
        _nukeArmed = false;
        break;
      }
      await new Promise(r => setTimeout(r, 300));
    }
  }
}

// ── API Discovery ──
// Prefer GnomTS (S5); keep JS fallback identical for no-bundle cases.
async function discoverPort() {
  if (window.GnomTS && typeof window.GnomTS.discoverApiBase === 'function') {
    const base = await window.GnomTS.discoverApiBase({
      protocol: location.protocol,
      origin: location.origin,
    });
    if (base) { API = base; return; }
    return;
  }
  if (location.protocol !== 'file:') { API = location.origin + '/api'; return; }
  for (const p of [3003, 3002, 3001, 3000]) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const r = await fetch(`http://127.0.0.1:${p}/api/stats`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (r.ok) { API = `http://127.0.0.1:${p}/api`; return; }
    } catch (e) { }
  }
}

async function api(method, path, body, opts) {
  if (window.GnomTS && typeof window.GnomTS.apiRequest === 'function') {
    return window.GnomTS.apiRequest(API, method, path, body, opts);
  }
  opts = opts || {};
  const timeoutMs = (typeof opts.timeout === 'number') ? opts.timeout : 15000;
  const controller = (typeof AbortController === 'function') ? new AbortController() : null;
  let timeoutId = null;
  if (controller) {
    timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  }
  try {
    const fetchOpts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) fetchOpts.body = JSON.stringify(body);
    if (controller) fetchOpts.signal = controller.signal;
    const r = await fetch(API + path, fetchOpts);
    const text = await r.text();
    const data = text ? safeJsonParse(text) : null;

    if (!r.ok) {
      // Logge präzise Fehlerinfo (Status + URL), damit Aufrufer unterscheiden
      // können zwischen 'leere Liste' und 'Backend kaputt'.
      const detail = (data && data.detail) ? data.detail : text.slice(0, 200);
      const err = new Error(`API ${method} ${path} → ${r.status}: ${detail}`);
      err.status = r.status;
      err.url = API + path;
      err.body = data;
      if (!opts.silent) console.error('[api]', err.message);
      throw err;
    }
    return data;
  } catch (e) {
    if (e && e.name === 'AbortError') {
      const err = new Error(`API ${method} ${path} timed out after ${timeoutMs}ms`);
      err.status = 0;
      err.url = API + path;
      err.timeout = true;
      if (!opts.silent) console.error('[api]', err.message);
      throw err;
    }
    if (e && e.status) throw e; // bereits oben konstruiert
    const err = new Error(`API ${method} ${path} → network error: ${e.message || e}`);
    err.status = 0;
    err.url = API + path;
    if (!opts.silent) console.error('[api]', err.message);
    throw err;
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}

function safeJsonParse(text) {
  if (window.GnomTS && typeof window.GnomTS.safeJsonParse === 'function') {
    return window.GnomTS.safeJsonParse(text);
  }
  try { return JSON.parse(text); } catch (_e) { return text; }
}

window.api = api;
window.safeJsonParse = safeJsonParse;

/** Escape HTML to prevent XSS when inserting dynamic content. */
function escapeHtml(str) {
  if (window.GnomTS && typeof window.GnomTS.escapeHtml === 'function') {
    return window.GnomTS.escapeHtml(str);
  }
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

/**
 * Sanitize HTML to prevent XSS from LLM-generated content.
 * Allows safe HTML tags for rendering but strips dangerous ones.
 */
function sanitizeHTML(html) {
    if (typeof html !== 'string') return '';
    const div = document.createElement('div');
    div.innerHTML = html;
    // Remove dangerous elements
    const dangerous = div.querySelectorAll('script, iframe[src], object, embed, form[action], link[rel=import], meta, base');
    dangerous.forEach(el => el.remove());
    // Remove dangerous attributes from all elements
    div.querySelectorAll('*').forEach(el => {
        for (const attr of [...el.attributes]) {
            const name = attr.name.toLowerCase();
            if (name.startsWith('on') || name === 'formaction' || 
                (name === 'href' && attr.value.trim().toLowerCase().startsWith('javascript:')) ||
                (name === 'src' && attr.value.trim().toLowerCase().startsWith('javascript:')) ||
                (name === 'action' && attr.value.trim().toLowerCase().startsWith('javascript:'))) {
                el.removeAttribute(attr.name);
            }
        }
    });
    return div.innerHTML;
}

// ── Preset Display and Activation ──
function showPresetInShowbox(preset) {
  const focusMap = {
    "Web Development": "Fokus auf sauberen HTML, CSS, JavaScript Code, Responsive Design, Barrierefreiheit, Performance und moderne Web-APIs.",
    "Graphic Design": "Fokus auf visuelle Ästhetik, Farbharmonien, Typografie, UI/UX Layouts, SVG-Generierung und Grafik-Design-Prinzipien.",
    "Audio Production": "Fokus auf Sound-Synthese, Web Audio API, Audio-Processing, Soundeffekte, Musiktheorie und akustische Gestaltung.",
    "Video Production": "Fokus auf Video-Streaming, Canvas-Animationen, CSS-Transitions, Video-Editing-Konzepte und visuelle Effekte.",
    "Marketing & Copy": "Fokus auf überzeugende Texte, SEO-Optimierung, Conversion-Rates, Social Media Strategien und zielgruppengerechte Ansprache.",
    "Content Creation": "Fokus auf überzeugende Texte, SEO-Optimierung, Content-Erstellung, Social Media Strategien und zielgruppengerechte Ansprache.",
    "Research & Analysis": "Fokus auf tiefgehende Recherche, Datenanalyse, Faktenprüfung, strukturierte Berichte und wissenschaftliche Genauigkeit."
  };
  const info = focusMap[preset] || "Allgemeine Unterstützung des Schwarms.";
  if (typeof showboxInterval !== 'undefined' && showboxInterval) clearInterval(showboxInterval);
  if (typeof showboxTimeout !== 'undefined' && showboxTimeout) clearTimeout(showboxTimeout);
  window.activeShowboxIndex = 99;
  window.showboxActive = true;
  
  const sb = document.getElementById('showbox');
  if (sb) {
    sb.classList.remove('glow-important', 'glow-agent');
    sb.style.setProperty('--showbox-glow-color', '');
    sb.innerHTML = `
      <div class="layer-content showbox-layer-content" id="showbox-text" style="opacity:0; transition: opacity 0.3s ease;">
        <div style="font-size: 1.2rem; margin-bottom: 12px; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; text-shadow: 0 0 10px rgba(0,229,255,0.4);">${preset}</div>
        <div style="font-size: 0.95rem; font-weight: normal; line-height: 1.5; color: rgba(255,255,255,0.9); padding: 0 20px;">${info}</div>
      </div>
    `;
    sb.classList.add('active-presentation');
    const sbText = document.getElementById('showbox-text');
    if (sbText) {
      if (typeof resizeShowboxText === 'function') {
        resizeShowboxText(sbText, sb);
      }
      setTimeout(() => { sbText.style.opacity = 1; }, 50);
    }
    if (typeof updateShowboxClocks === 'function') {
      updateShowboxClocks();
    }
  }
}

async function changePreset(preset) {
  try {
    const res = await api('POST', '/admin/preset', { preset });
    if (res && res.status === 'ok') {
      toast(`Preset gewechselt zu: ${preset}`, 'success');
      showPresetInShowbox(preset);
      if (typeof refreshChat === 'function') {
        setTimeout(refreshChat, 1000);
      }
    } else {
      toast(`Fehler beim Wechseln des Presets`, 'error');
    }
  } catch (e) {
    console.error("Failed to change preset", e);
    toast(`Fehler: ${e.message}`, 'error');
  }
}

async function loadActivePreset() {
  try {
    const presetsRes = await api('GET', '/admin/presets');
    if (presetsRes && presetsRes.presets) {
      const el = document.getElementById('preset-select');
      if (el) {
        el.innerHTML = presetsRes.presets.map(name => {
          let emoji = '⚙️';
          if (name.includes('Web')) emoji = '💻';
          else if (name.includes('Design') || name.includes('Graphic')) emoji = '🎨';
          else if (name.includes('Audio')) emoji = '🎵';
          else if (name.includes('Video')) emoji = '🎬';
          else if (name.includes('Content') || name.includes('Marketing') || name.includes('Creation')) emoji = '✍️';
          else if (name.includes('Research')) emoji = '🔍';
          return `<option value="${name}">${emoji} ${name}</option>`;
        }).join('');
      }
    }
    const res = await api('GET', '/admin/preset');
    if (res && res.preset) {
      const el = document.getElementById('preset-select');
      if (el) el.value = res.preset;
    }
  } catch (e) {
    console.error("Failed to load active preset", e);
  }
}

// ── Colors ──
// Prefer GnomTS (TypeScript layer, S5) when loaded; keep JS fallback identical.
function agentColor(name) {
  if (window.GnomTS && typeof window.GnomTS.agentColor === 'function') {
    return window.GnomTS.agentColor(name);
  }
  if (!name) return '#00E5FF';
  const n = name.toLowerCase();
  if (KNOWN_COLORS[n]) return KNOWN_COLORS[n];
  let h = 5381; for (let i = 0; i < name.length; i++) h = ((h << 5) + h) + name.charCodeAt(i);
  return P_COLORS[Math.abs(h) % P_COLORS.length];
}

function groupColor(g) {
  if (!g) return null;
  let h = 5381; for (let i = 0; i < g.length; i++) h = ((h << 5) + h) + g.charCodeAt(i);
  return P_COLORS[Math.abs(h) % P_COLORS.length];
}

// ── Interval cleanup registry ──
function _trackInterval(fn, ms) { const id = setInterval(fn, ms); _intervalIds.push(id); return id; }
window.addEventListener('beforeunload', () => {
  _intervalIds.forEach(id => clearInterval(id));
  if (window.showboxTimerInterval) clearInterval(window.showboxTimerInterval);
  if (typeof showboxInterval !== 'undefined' && showboxInterval) clearInterval(showboxInterval);
  if (typeof panelShowboxInterval !== 'undefined' && panelShowboxInterval) clearInterval(panelShowboxInterval);
});

// ── Stats ──
async function updateStats() {
  const s = await api('GET', '/stats');
  if (!s) return;

  // S5: pure formatters from GnomTS; DOM write stays here
  if (window.GnomTS && typeof window.GnomTS.formatStatsPanel === 'function') {
    const panel = window.GnomTS.formatStatsPanel(s, agents || []);
    const elAgents = document.getElementById('s-agents');
    if (elAgents) elAgents.textContent = panel.agents;
    const elMem = document.getElementById('s-memory');
    if (elMem) elMem.textContent = panel.memory;
    const elTok = document.getElementById('s-tokens');
    if (elTok) elTok.textContent = panel.tokens;
    if (document.getElementById('s-queue') && panel.queue != null) {
      document.getElementById('s-queue').textContent = panel.queue;
    }
    if (document.getElementById('s-leases')) {
      document.getElementById('s-leases').textContent = panel.leases;
      document.getElementById('s-leases').title = panel.leasesTitle;
    }
    if (document.getElementById('s-lasterr')) {
      document.getElementById('s-lasterr').textContent = panel.lastErr;
      document.getElementById('s-lasterr').title = panel.lastErrTitle;
    }
    const elLlm = document.getElementById('s-llm');
    if (elLlm) {
      elLlm.textContent = panel.llm || '—';
      elLlm.title = panel.llmTitle || '';
    }
    return;
  }

  const sysNames = ['soulag', 'generalag', 'securityag', 'watchdogag'];
  const totalA = s.agents ?? agents.length;
  const sysA = s.sys_agents ?? agents.filter(a => sysNames.includes((a.name || '').toLowerCase())).length;
  const workA = s.work_agents ?? (totalA - sysA);
  document.getElementById('s-agents').textContent = `${totalA} (Sys: ${sysA} | Work: ${workA})`;
  document.getElementById('s-memory').textContent = s.memory ?? 0;
  if (document.getElementById('s-tokens')) {
    const tFree = s.tokens_free ?? 0;
    const tPay = s.tokens_pay ?? 0;
    document.getElementById('s-tokens').textContent = `Free: ${tFree} | Pay: ${tPay}`;
  }
  // Ops panel: queue / leases / last error
  if (document.getElementById('s-queue') && s.queue) {
    const q = s.queue;
    document.getElementById('s-queue').textContent =
      `${q.pending || 0}/${q.processing || 0}/${q.dead_letter || 0}`;
  }
  if (document.getElementById('s-leases')) {
    const n = (s.leases && s.leases.length) || 0;
    const who = (s.leases || []).map(l => l.recipient).filter(Boolean).slice(0, 3).join(',');
    document.getElementById('s-leases').textContent = n ? `${n}${who ? ' ' + who : ''}` : '0';
    document.getElementById('s-leases').title = (s.leases || [])
      .map(l => `#${l.id} ${l.recipient}`).join('\n') || 'no active leases';
  }
  if (document.getElementById('s-lasterr')) {
    if (s.last_error) {
      const e = s.last_error;
      document.getElementById('s-lasterr').textContent = `${e.status} ${e.recipient || ''}`.trim();
      document.getElementById('s-lasterr').title = JSON.stringify(e);
    } else {
      document.getElementById('s-lasterr').textContent = '—';
    }
  }
  const elLlm = document.getElementById('s-llm');
  if (elLlm) {
    if (window.GnomTS && typeof window.GnomTS.formatLlmLine === 'function') {
      const llmFmt = window.GnomTS.formatLlmLine(s.llm);
      elLlm.textContent = llmFmt.text;
      elLlm.title = llmFmt.title;
    } else if (s.llm && s.llm.summary) {
      elLlm.textContent = s.llm.summary;
      elLlm.title = JSON.stringify(s.llm.agents || {}, null, 0);
    } else {
      elLlm.textContent = '—';
    }
  }
}

// ── Easter Eggs ──
window.coffeeTimer = null;
window.coffeeFleeCount = 0;
window.showCoffeeBreak = () => {
  const el = document.getElementById('coffee-overlay');
  if (!el) return;
  el.style.transition = 'none';
  el.style.bottom = '30px';
  el.style.right = '30px';
  el.style.top = 'auto';
  el.style.left = 'auto';
  el.style.display = 'block';
  window.coffeeFleeCount = 0;
  if (typeof speak === 'function') speak("Take it easy. Drink coffee.");
  clearTimeout(window.coffeeTimer);
  window.coffeeTimer = setTimeout(() => { el.style.display = 'none'; }, 20000);
};

window.fleeCoffee = () => {
  window.coffeeFleeCount++;
  const el = document.getElementById('coffee-overlay');
  if (!el) return;
  if (window.coffeeFleeCount >= 3) {
    el.style.display = 'none';
    clearTimeout(window.coffeeTimer);
    return;
  }
  el.style.transition = 'all 0.15s cubic-bezier(0.25, 1, 0.5, 1)';
  const maxX = Math.max(10, window.innerWidth - el.offsetWidth - 20);
  const maxY = Math.max(10, window.innerHeight - el.offsetHeight - 20);
  const rx = Math.max(10, Math.floor(Math.random() * maxX));
  const ry = Math.max(10, Math.floor(Math.random() * maxY));
  el.style.bottom = 'auto';
  el.style.right = 'auto';
  el.style.left = rx + 'px';
  el.style.top = ry + 'px';
};

window.showUfoAttack = () => {
  const o = document.getElementById('ufo-overlay');
  if (o) {
    o.style.display = 'flex';
    setTimeout(() => { o.style.display = 'none'; }, 600000);
  }
};

window.showGhost = () => {
  const o = document.getElementById('ghost-overlay');
  if (o) {
    const newGhost = o.cloneNode(true);
    o.parentNode.replaceChild(newGhost, o);
    newGhost.style.display = 'flex';
    setTimeout(() => { newGhost.style.display = 'none'; }, 120000);
  }
};

window.trackView = (viewName) => {
  // Guard against losing unsaved changes when navigating away from the LLM
  // page (or any other view that registered pending changes).
  if (window.llmPendingChanges && typeof window.llmPendingChanges.hasAny === 'function'
      && window.llmPendingChanges.hasAny()
      && window.currentView === 'llm'
      && viewName !== 'llm') {
    const ok = window.confirm(
      'Ungespeicherte Änderungen — wirklich verlassen?\n\n' +
      'Offen: ' + window.llmPendingChanges.summary() + '\n\n' +
      'OK = verwerfen, Abbrechen = zurück zur Seite.'
    );
    if (!ok) return; // Stay on the current view
    // User chose to discard → wipe pending changes
    window.llmPendingChanges.clear();
    if (typeof window.updateSaveBadge === 'function') window.updateSaveBadge();
  }
  // Agent-Border-Rahmen entfernen, sobald wir das Agent-Tuning-Panel verlassen.
  if (window.currentView === 'agent-tuning' && viewName !== 'agent-tuning') {
    if (typeof window.clearAgentBorder === 'function') window.clearAgentBorder();
  }
  window.currentView = viewName;
  window.updateBackButtonState();
};

window.updateBackButtonState = () => {
  const btn = document.getElementById('btn-back');
  if (btn) {
    const isNotChat = window.currentView !== 'war-room';
    btn.disabled = !isNotChat;
    btn.style.opacity = isNotChat ? '1' : '0.4';
    btn.style.pointerEvents = isNotChat ? 'auto' : 'none';
  }
};

window.goBackView = () => {
  if (window.currentView !== 'war-room') {
    if (typeof showWarRoom === 'function') showWarRoom();
  }
};

// Browser-level guard (refresh / tab close).
window.__llmBeforeUnload = (e) => {
  if (window.llmPendingChanges && typeof window.llmPendingChanges.hasAny === 'function'
      && window.llmPendingChanges.hasAny()) {
    e.preventDefault();
    e.returnValue = 'Ungespeicherte Änderungen — wirklich verlassen?';
    return e.returnValue;
  }
};
window.addEventListener('beforeunload', window.__llmBeforeUnload);

// ─────────────────────────────────────────────────────────────────
// globalSave — single Save button wired to the header. Persists
//   1) LLM page pending changes (System + Worker agents, Web Search,
//      TTS, inline keys for those services)
//   2) Agent optimizer settings (worker sidebar) for the selected agent
//   3) A backup-file write of the current DB state.
// ─────────────────────────────────────────────────────────────────

async function flushLlmPageChanges() {
  if (!window.llmPendingChanges) return { ok: true, saved: 0 };

  const summary = { agents: 0, web_search: false, tts: false, keys: 0, errors: [] };

  // 1. Service configs (web_search / tts). Save inline keys first (if any),
  //    then the chosen provider + model selection.
  for (const svc of ['web_search', 'tts']) {
    const cfg = window.llmPendingChanges[svc];
    if (!cfg || (!cfg.provider && !cfg.model && !cfg.inline_key)) continue;
    try {
      // If user typed a key inline, test+save it before persisting the binding.
      if (cfg.inline_key && cfg.provider) {
        const t = await fetch('/api/llm/test', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: cfg.inline_key, provider: cfg.provider, label: svc.toUpperCase() + '_API_KEY' })
        });
        const td = t.ok ? await t.json() : { valid: false };
        if (!td.valid) {
          summary.errors.push(`${svc}: Key ungültig (${td.info || 'unknown'})`);
          continue;
        }
        const kid = `${cfg.provider}_${Date.now()}_${Math.random().toString(36).slice(2,6)}`;
        // MERGE with existing keys — vorher wurde nur der eine Key gepostet,
        // was via save_keys() die komplette llm_keys-DB überschrieb und alle
        // anderen Provider-Keys (z.B. MiniMax) gelöscht hat.
        let existing = {};
        try {
          const g = await fetch('/api/llm/keys');
          if (g.ok) existing = await g.json();
        } catch (_) {}
        existing[kid] = { provider: cfg.provider, key: cfg.inline_key, label: svc.toUpperCase() + '_API_KEY', valid: true };
        await fetch('/api/llm/keys', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(existing)
        });
        summary.keys++;
      }
      // Persist the service binding.
      const payload = {};
      payload[svc] = { provider: cfg.provider, model: cfg.model };
      const r = await fetch('/api/llm/service', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!r.ok) {
        summary.errors.push(`${svc}: HTTP ${r.status}`);
      } else {
        if (svc === 'web_search') summary.web_search = true;
        if (svc === 'tts')        summary.tts = true;
      }
    } catch (e) {
      summary.errors.push(`${svc}: ${e.message}`);
    }
  }

  // 2. Agent routing changes. Backend expects {agent_name: {provider, model}}
  //    via POST /api/llm/agents (the same endpoint loadLLMConfig uses).
  const agents = window.llmPendingChanges.agents || {};
  if (Object.keys(agents).length > 0) {
    try {
      const body = {};
      Object.entries(agents).forEach(([name, cfg]) => {
        body[name.toLowerCase()] = cfg;
      });
      const r = await fetch('/api/llm/agents', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!r.ok) summary.errors.push(`agents: HTTP ${r.status}`);
      else summary.agents = Object.keys(agents).length;
    } catch (e) {
      summary.errors.push('agents: ' + e.message);
    }
  }

  // Clear the pending tracker regardless — partial failures are surfaced
  // through summary.errors and the toast below.
  if (window.llmPendingChanges.clear) window.llmPendingChanges.clear();
  if (typeof window.updateSaveBadge === 'function') window.updateSaveBadge();

  return { ok: summary.errors.length === 0, summary };
}

async function writeBackupFile() {
  try {
    const r = await fetch('/api/admin/backup', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    if (!r.ok) return { ok: false, info: 'HTTP ' + r.status };
    const d = await r.json();
    return { ok: d.status === 'ok', info: d.path || d.info || d.status, raw: d };
  } catch (e) {
    return { ok: false, info: e.message };
  }
}

window.globalSave = async () => {
  const log = [];
  let hadChanges = false;

  // 1) LLM page (System + Worker agents + Web Search + TTS)
  const llmRes = await flushLlmPageChanges();
  if (llmRes && (llmRes.summary.agents || llmRes.summary.web_search || llmRes.summary.tts || llmRes.summary.keys || llmRes.summary.errors.length)) {
    hadChanges = true;
    if (llmRes.summary.agents)   log.push(`${llmRes.summary.agents} Agent-Routing(s)`);
    if (llmRes.summary.web_search) log.push('Web Search');
    if (llmRes.summary.tts)        log.push('TTS');
    if (llmRes.summary.keys)     log.push(`${llmRes.summary.keys} neue Key(s)`);
    if (llmRes.summary.errors.length) {
      toast('Fehler beim Speichern: ' + llmRes.summary.errors.join('; '), 'error');
    }
  }

  // 2) Agent-tuning sidebar for the currently selected agent.
  if (window.selectedId && typeof saveAgentOptimizerSettings === 'function') {
    await saveAgentOptimizerSettings(window.selectedId);
    hadChanges = true;
    log.push('Agent-Einstellungen');
  }

  // 3) Backup file write — always attempt, even if nothing else changed, so
  //    the user gets a fresh snapshot on every global Save.
  const backup = await writeBackupFile();
  if (backup.ok) {
    hadChanges = true;
    if (backup.info) log.push('Backup: ' + backup.info.split('/').pop());
  } else if (!hadChanges) {
    // No changes at all and backup failed → informational.
    toast('Nichts zu speichern. (Backup-Skript: ' + (backup.info || 'unbekannt') + ')', 'info');
    return;
  } else {
    log.push('Backup: FEHLGESCHLAGEN (' + (backup.info || '?') + ')');
  }

  if (hadChanges) {
    const msg = log.length ? 'Gespeichert: ' + log.join(' · ') : 'Gespeichert.';
    toast(msg, 'success');
  }

  // Refresh LLM-page caches so the badges / dropdowns reflect the saved state.
  if (typeof window.__llmRefreshAfterSave === 'function') window.__llmRefreshAfterSave();
};

window.getAgentHelpText = function(name, desc) {
  const n = (name || '').toLowerCase();
  if (n === 'generalag') {
    return '👑 <b>Commander-V50 (Koordinator):</b><br><br>Er ist das koordinierende Oberhaupt des Schwarms. Seine Aufgabe ist es, komplexe Benutzeranfragen zu analysieren, sie in logische Teilaufgaben zu zerlegen und diese gezielt an die spezialisierten Worker-Agenten zu delegieren. Am Ende führt er die Teilergebnisse zusammen.';
  } else if (n === 'soulag') {
    return '🧠 <b>Memex-50 (Gedächtnis & Kontext):</b><br><br>Er verwaltet das kollektive Langzeit- und Kurzzeitgedächtnis des Schwarms. Memex-50 speichert historische Interaktionen und Fakten in einem Vektorindex (FAISS) und lädt bei neuen Anfragen automatisch die relevantesten Kontextinformationen.';
  } else if (n === 'watchdogag') {
    return '🛡️ <b>Sentry-V50 (Regel-Wächter):</b><br><br>Ein Wächter aus massivem Messing, der die Einhaltung aller Sicherheitsregeln und Verzeichnispfade überwacht und illegale Systemzugriffe blockiert.';
  } else if (n === 'securityag') {
    return '🛡️ <b>Securitron-V50 (Sicherheits-Auditor):</b><br><br>Ein verchromter Sicherheitswächter, der Code-Dateien und Befehle vor Ausführung auf Schadcode und Schwachstellen analysiert.';
  } else if (n === 'coderag') {
    return '💻 <b>Turing-V50 (Entwickler):</b><br><br>Ein relaisgesteuerter Programmierer. Er schreibt, analysiert und optimiert Quellcode in diversen Programmiersprachen (Python, JS, HTML/CSS) und repariert Bugs.';
  } else if (n === 'writerag') {
    return '✍️ <b>Scribe-V50 (Redakteur & Doku):</b><br><br>Ein mechanischer Tastenschreiber. Er verfasst Texte jeglicher Art auf exzellentem sprachlichem Niveau und feilt an CTAs und Slogans.';
  } else if (n === 'researcherag') {
    return '🔍 <b>Archive-V50 (Rechercheur):</b><br><br>Ein Lochkarten-Archivar, der Fakten sammelt, das Web durchsucht und technische Dokumentationen auswertet, um dem Team fundierte Daten zuzuliefern.';
  } else if (n === 'editorag') {
    return '🔎 <b>Audit-V50 (Qualitätskontrolle):</b><br><br>Er führt die Endabnahme durch. Jeder Text und jeder Code, der von den anderen Worker-Agenten erzeugt wird, wird auf logische Fehler und Einhaltung aller Vorgaben geprüft.';
  }
  return `🤖 <b>${name}:</b><br><br>${desc || 'Ein spezialisierter Agent des Gnom-Hub Schwarms, der zur Erledigung deiner Aufgaben beiträgt.'}`;
};


