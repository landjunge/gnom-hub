/* =================================================================
   app.js — mc707 WebUI main app (Alpine.js)
   =================================================================
   Single global Alpine store ``mc707``. Exposes state + methods.
   Connects to the backend on init:
     1. GET /api/state  — full snapshot
     2. WebSocket /ws   — live updates
   Every user action goes through Api.* (REST) → backend → response
   is rendered back into the Alpine state. The WebSocket is the
   secondary path for state propagation (so an external mutation —
   e.g. from the agent or another UI tab — still syncs the sliders).
   ================================================================= */

document.addEventListener('alpine:init', () => {
  Alpine.data('mc707', () => ({
    // -------------------- STATE --------------------
    state: {
      is_mock: true,
      version: '?',
      soundDir: '',
      registryNames: [],
      diskSounds: [],
      currentSound: '',
      newSoundName: '',   // bound to the inline "new sound" form
      currentScene: null,
      tempo: 120,
      playing: false,
      mixer: {},          // { 1: {mute, solo, volume, pan}, ... }
      fx: {},             // { cutoff: 64, reverb: 0, ... }
      arp: { on: false, rate: 64, gate: 64, style: 0, octave: 0 },
      activeClips: {},    // { "1-1": true, ... } for visual highlight
      tones: {},          // { 1: toneNum, 2: toneNum, ... }
      cachedParams: {},   // { paramName: value } from SoundEditor
      knownParams: [],    // [paramName, ...]
    },

    // -------------------- WS --------------------
    ws: {
      client: null,
      connected: false,
      lastEvent: '',
    },

    // -------------------- CONSTANTS --------------------
    effectsList: [
      { key: 'cutoff',     label: 'Cutoff' },
      { key: 'resonance',  label: 'Resonance' },
      { key: 'attack',     label: 'Attack' },
      { key: 'decay',      label: 'Decay' },
      { key: 'sustain',    label: 'Sustain' },
      { key: 'release',    label: 'Release' },
      { key: 'reverb',     label: 'Reverb' },
      { key: 'delay',      label: 'Delay' },
      { key: 'chorus',     label: 'Chorus' },
      { key: 'distortion', label: 'Distortion' },
    ],

    arpStyles: [
      'Up', 'Down', 'UpDown', 'Random',
    ],

    // =================================================================
    // INIT
    // =================================================================
    async init() {
      // Initialise mixer per-track defaults
      for (let t = 1; t <= 8; t++) {
        this.state.mixer[t] = { mute: false, solo: false, volume: 100, pan: 64 };
      }

      // WebSocket first so we get live updates while the snapshot loads
      this._setupWebSocket();

      // Snapshot
      try {
        const snap = await Api.getState();
        this._applySnapshot(snap);
      } catch (e) {
        console.error('Failed to load /api/state', e);
      }

      // Live status (scene / tempo / tones) — these aren't in /api/state
      try {
        const status = await Api.getStatus();
        if (status) {
          if (status.scene != null) this.state.currentScene = status.scene;
          if (status.tempo != null) this.state.tempo = status.tempo;
          if (status.tones) this.state.tones = status.tones;
        }
      } catch (e) {
        console.warn('Status fetch failed (cache-only is fine)', e);
      }

      // Version from /health
      try {
        const h = await fetch('/health').then(r => r.json());
        if (h && h.version) this.state.version = h.version;
      } catch (_) { /* ignore */ }
    },

    // =================================================================
    // SNAPSHOT / SYNC
    // =================================================================
    _applySnapshot(snap) {
      this.state.is_mock = !!snap.is_mock;
      this.state.soundDir = snap.sound_dir || '';
      this.state.registryNames = snap.registry_names || [];
      this.state.diskSounds = snap.disk_sounds || [];
      this.state.knownParams = snap.known_params || [];
      this.state.cachedParams = { ...(snap.cached_params || {}) };

      // Auto-select first sound if any
      if (!this.state.currentSound && this.state.registryNames.length > 0) {
        this.state.currentSound = this.state.registryNames[0];
      }
    },

    // =================================================================
    // WEBSOCKET
    // =================================================================
    _setupWebSocket() {
      const c = new MC707WebSocket();
      c.onStateChange((connected) => { this.ws.connected = connected; });
      c.onEvent((type, data) => this._handleWsEvent(type, data));
      this.ws.client = c;
      c.connect();
    },

    _handleWsEvent(type, data) {
      switch (type) {
        case 'transport_changed':
          if (data.playing != null) this.state.playing = !!data.playing;
          if (data.tempo != null) this.state.tempo = data.tempo;
          break;
        case 'scene_changed':
          if (data.index != null) this.state.currentScene = data.index;
          break;
        case 'clip_triggered': {
          const key = `${data.track}-${data.clip}`;
          this.state.activeClips[key] = true;
          // Clear after 1.2s for a visual flash
          setTimeout(() => {
            delete this.state.activeClips[key];
            // Trigger reactivity by reassigning
            this.state.activeClips = { ...this.state.activeClips };
          }, 1200);
          break;
        }
        case 'param_changed':
          if (data.param && data.value != null) {
            this.state.cachedParams = {
              ...this.state.cachedParams,
              [data.param]: data.value,
            };
          }
          break;
        case 'sound_registered':
        case 'sound_removed': {
          // Refresh registry list
          Api.sounds.list()
            .then(r => { this.state.registryNames = r.names || []; })
            .catch(() => {});
          break;
        }
        case 'sound_saved':
        case 'sound_loaded': {
          // Refresh disk list
          Api.sounds.listDisk()
            .then(r => { this.state.diskSounds = r.names || []; })
            .catch(() => {});
          // If loaded, also refresh registry
          if (type === 'sound_loaded') {
            Api.sounds.list()
              .then(r => {
                this.state.registryNames = r.names || [];
                if (data.name && r.names.includes(data.name)) {
                  this.state.currentSound = data.name;
                }
              })
              .catch(() => {});
          }
          break;
        }
        case 'state_reset':
          // Re-fetch snapshot
          Api.getState()
            .then(snap => this._applySnapshot(snap))
            .catch(() => {});
          break;
      }
    },

    // =================================================================
    // TRANSPORT
    // =================================================================
    transport: {
      play() {
        Api.transport.play()
          .then(() => { this.state.playing = true; })
          .catch(e => this._err('Play', e));
      },
      stop() {
        Api.transport.stop()
          .then(() => { this.state.playing = false; })
          .catch(e => this._err('Stop', e));
      },
      pause() {
        Api.transport.pause()
          .then(() => { this.state.playing = false; })
          .catch(e => this._err('Pause', e));
      },
      setTempo(bpm) {
        const v = Number(bpm);
        if (!isFinite(v)) return;
        Api.transport.tempo(v)
          .then(r => { if (r && r.bpm != null) this.state.tempo = r.bpm; })
          .catch(e => this._err('Set tempo', e));
      },
    },

    // =================================================================
    // SCENES
    // =================================================================
    scenes: {
      select(index) {
        Api.scenes.select(index)
          .then(() => { this.state.currentScene = index; })
          .catch(e => this._err('Select scene', e));
      },
      next() {
        Api.scenes.next()
          .then(r => {
            const idx = r && r.data && r.data.index;
            if (idx != null) this.state.currentScene = idx;
          })
          .catch(e => this._err('Next scene', e));
      },
      previous() {
        Api.scenes.previous()
          .then(r => {
            const idx = r && r.data && r.data.index;
            if (idx != null) this.state.currentScene = idx;
          })
          .catch(e => this._err('Previous scene', e));
      },
    },

    // =================================================================
    // CLIPS / MIXER
    // =================================================================
    clips: {
      trigger(track, clip) {
        Api.clips.trigger(track, clip).catch(e => this._err('Trigger clip', e));
      },
      stopAll() {
        Api.clips.stopAll().catch(e => this._err('Stop all', e));
      },
      toggleMute(track) {
        Api.clips.mute(track)
          .then(() => {
            const m = this.state.mixer[track];
            if (m) { m.mute = !m.mute; }
          })
          .catch(e => this._err('Mute', e));
      },
      toggleSolo(track) {
        Api.clips.solo(track)
          .then(() => {
            const m = this.state.mixer[track];
            if (m) { m.solo = !m.solo; }
          })
          .catch(e => this._err('Solo', e));
      },
      setVolume(track, value) {
        const v = Number(value);
        if (!isFinite(v)) return;
        const m = this.state.mixer[track];
        if (m) m.volume = v;
        Api.clips.volume(track, v).catch(e => this._err('Volume', e));
      },
      setPan(track, value) {
        const v = Number(value);
        if (!isFinite(v)) return;
        const m = this.state.mixer[track];
        if (m) m.pan = v;
        Api.clips.pan(track, v).catch(e => this._err('Pan', e));
      },
    },

    // =================================================================
    // SOUNDS
    // =================================================================
    sounds: {
      loadFromRegistry(name) {
        if (!name) return;
        // Pull the current editor cache so the sliders have something to show
        Api.sounds.list()
          .then(() => this._refreshParamsFor(name))
          .catch(e => this._err('Load sound', e));
      },
      loadFromDisk(name) {
        if (!name) return;
        Api.sounds.loadDisk(name)
          .then(r => {
            if (r && r.data && r.data.name) {
              this.state.currentSound = r.data.name;
              return this._refreshParamsFor(r.data.name);
            }
          })
          .catch(e => this._err('Load from disk', e));
      },
      save() {
        if (!this.state.currentSound) return;
        Api.sounds.saveDisk(this.state.currentSound)
          .catch(e => this._err('Save', e));
      },
      applyAll() {
        if (!this.state.currentSound) return;
        Api.sounds.applyAll(this.state.currentSound)
          .then(() => this._refreshParamsFor(this.state.currentSound))
          .catch(e => this._err('Apply', e));
      },
      remove() {
        const name = this.state.currentSound;
        if (!name) return;
        // No native confirm() — some browsers block it. We rely on the
        // explicit "🗑 Delete" button + the sound being unsaved to disk
        // (use 💾 Save first) as the user's undo path. Cheap & predictable.
        Api.sounds.remove(name)
          .then(() => {
            this.state.currentSound = '';
            this.state.cachedParams = {};
            // Refresh registry
            return Api.sounds.list();
          })
          .then(r => { if (r) this.state.registryNames = r.names || []; })
          .catch(e => this._err('Delete', e));
      },
      createNew(name) {
        const finalName = (name || '').trim();
        if (!finalName) return;
        // Build a default Sound — matches mc707.models.sound.Sound defaults
        const sound = {
          name: finalName,
          category: 'other',
          oscillator: { wave: 'saw', pitch: 0, level: 100 },
          filter: { type: 'lpf', cutoff: 64, resonance: 0, env_amount: 32 },
          amp_envelope: { attack: 0, decay: 64, sustain: 96, release: 64 },
          filter_envelope: { attack: 0, decay: 64, sustain: 64, release: 64, amount: 32 },
          lfo: { rate: 32, depth: 0, sync: false, target: 'pitch' },
        };
        Api.sounds.create(sound)
          .then(() => Api.sounds.list())
          .then(r => {
            this.state.registryNames = r.names || [];
            this.state.currentSound = finalName;
            this.state.cachedParams = {};   // fresh sound → reset cache
          })
          .catch(e => this._err('Create sound', e));
      },
      setParam(paramName, rawValue) {
        const name = this.state.currentSound;
        if (!name) return;
        const value = Number(rawValue);
        if (!isFinite(value) || value < 0 || value > 127) return;
        // Optimistic local update
        this.state.cachedParams = {
          ...this.state.cachedParams,
          [paramName]: value,
        };
        Api.sounds.setParam(name, paramName, value)
          .catch(e => this._err(`Set ${paramName}`, e));
      },
    },

    _refreshParamsFor(name) {
      // Pull the latest cached params for this sound. The backend exposes
      // /api/sounds/{name}/params which returns the editor cache (session-wide).
      return Api.sounds.list()
        .then(r => { if (r) this.state.registryNames = r.names || []; })
        .then(() => fetch(`/api/sounds/${encodeURIComponent(name)}/params`))
        .then(r => r.json())
        .then(j => {
          if (j && j.params) {
            this.state.cachedParams = { ...j.params };
          }
        })
        .catch(e => this._err('Refresh params', e));
    },

    // =================================================================
    // EFFECTS
    // =================================================================
    effects: {
      set(name, value) {
        const v = Number(value);
        if (!isFinite(v)) return;
        this.state.fx[name] = v;
        Api.effects.set(name, v).catch(e => this._err(`Effect ${name}`, e));
      },
    },

    // =================================================================
    // ARPEGGIATOR
    // =================================================================
    arp: {
      on() {
        Api.arp.on()
          .then(() => { this.state.arp.on = true; })
          .catch(e => this._err('Arp on', e));
      },
      off() {
        Api.arp.off()
          .then(() => { this.state.arp.on = false; })
          .catch(e => this._err('Arp off', e));
      },
      set(field, value) {
        const v = Number(value);
        if (!isFinite(v)) return;
        this.state.arp[field] = v;
        const fn = Api.arp[field];
        if (typeof fn !== 'function') return;
        fn(v).catch(e => this._err(`Arp ${field}`, e));
      },
    },

    // =================================================================
    // HELPERS
    // =================================================================
    paramValue(name) {
      const v = this.state.cachedParams[name];
      return v != null ? v : 0;
    },

    signedValue(raw, zero) {
      // Display a value that's stored as unsigned 7-bit but represents a
      // signed quantity (offset by ``zero``).
      const v = Number(raw);
      if (!isFinite(v)) return '—';
      const signed = v - zero;
      return signed > 0 ? `+${signed}` : `${signed}`;
    },

    _err(label, e) {
      console.warn(`[mc707] ${label}: ${e && e.message ? e.message : e}`);
    },
  }));
});
