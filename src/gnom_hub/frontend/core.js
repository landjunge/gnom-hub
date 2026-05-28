/* ═══════════════════════════════════════════
   GNOM-HUB — Core Logic & Shared State
   ═══════════════════════════════════════════ */

// Shared Globals
var API = '';
var agents = [];
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
  const c = document.getElementById('toasts');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 300); }, 10500);
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
async function discoverPort() {
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

async function api(method, path, body) {
  try {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(API + path, opts);
    if (!r.ok) throw new Error(r.status);
    const text = await r.text();
    return text ? JSON.parse(text) : null;
  } catch (e) { console.error('API:', path, e); return null; }
}
window.api = api;

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
function agentColor(name) {
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
  if (s) {
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

window.globalSave = async () => {
  let savedSomething = false;
  
  const llmPanel = document.getElementById('llm-panel');
  if (llmPanel && window.getComputedStyle(llmPanel).display !== 'none') {
    if (typeof saveKeysOnly === 'function') {
      await saveKeysOnly();
    }
    if (typeof saveAgentLLMs === 'function') {
      await saveAgentLLMs();
    }
    savedSomething = true;
  }
  
  if (window.selectedId) {
    if (typeof saveAgentOptimizerSettings === 'function') {
      await saveAgentOptimizerSettings(window.selectedId);
    }
    savedSomething = true;
  }
  
  if (!savedSomething) {
    toast('Nichts zu speichern.', 'info');
  }
};

