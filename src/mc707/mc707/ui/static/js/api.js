/* =================================================================
   api.js — thin REST client for the mc707 WebUI backend
   =================================================================
   Exposes a global ``Api`` object with one method per route group.
   Every method returns a Promise that resolves with the JSON body
   (FastAPI already serialises everything via Pydantic).
   Errors are normalised: throws ``ApiError`` with .status and .detail.
   ================================================================= */

(function () {
  'use strict';

  class ApiError extends Error {
    constructor(status, message, detail) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.detail = detail;
    }
  }

  async function request(method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== undefined) {
      opts.body = JSON.stringify(body);
    }
    let resp;
    try {
      resp = await fetch(path, opts);
    } catch (e) {
      throw new ApiError(0, `Network error: ${e.message}`, null);
    }
    const text = await resp.text();
    let json = null;
    if (text) {
      try { json = JSON.parse(text); } catch (_) { /* non-JSON */ }
    }
    if (!resp.ok) {
      const detail = (json && (json.detail || json.error)) || text || resp.statusText;
      throw new ApiError(resp.status, `HTTP ${resp.status}: ${detail}`, detail);
    }
    return json;
  }

  const Api = {
    ApiError,

    // -------------------- State / Discovery --------------------

    getState() {
      return request('GET', '/api/state');
    },

    getStatus() {
      return request('GET', '/api/status');
    },

    // -------------------- Transport --------------------

    transport: {
      play() { return request('POST', '/api/transport/play'); },
      stop() { return request('POST', '/api/transport/stop'); },
      pause() { return request('POST', '/api/transport/pause'); },
      tempo(bpm) { return request('POST', '/api/transport/tempo', { bpm }); },
    },

    // -------------------- Scenes --------------------

    scenes: {
      select(index) { return request('POST', '/api/scenes/select', { index }); },
      next() { return request('POST', '/api/scenes/next'); },
      previous() { return request('POST', '/api/scenes/previous'); },
      current() { return request('GET', '/api/scenes/current'); },
    },

    // -------------------- Clips / Mixer --------------------

    clips: {
      trigger(track, clip) { return request('POST', '/api/clips/trigger', { track, clip }); },
      stop(track) { return request('POST', `/api/clips/${track}/stop`); },
      stopAll() { return request('POST', '/api/clips/stop-all'); },
      mute(track) { return request('POST', `/api/clips/${track}/mute`); },
      solo(track) { return request('POST', `/api/clips/${track}/solo`); },
      volume(track, value) { return request('POST', `/api/clips/${track}/volume`, { track, value }); },
      pan(track, value) { return request('POST', `/api/clips/${track}/pan`, { track, value }); },
    },

    // -------------------- Sounds --------------------

    sounds: {
      list() { return request('GET', '/api/sounds'); },
      get(name) { return request('GET', `/api/sounds/${encodeURIComponent(name)}`); },
      create(sound) { return request('POST', '/api/sounds', { sound }); },
      remove(name) { return request('DELETE', `/api/sounds/${encodeURIComponent(name)}`); },
      getParam(name, param) {
        return request('GET', `/api/sounds/${encodeURIComponent(name)}/params/${encodeURIComponent(param)}`);
      },
      setParam(name, param, value) {
        return request('POST', `/api/sounds/${encodeURIComponent(name)}/params/${encodeURIComponent(param)}`, { value });
      },
      apply(name, params) {
        return request('POST', `/api/sounds/${encodeURIComponent(name)}/apply`, { sound: null, params });
      },
      applyAll(name) {
        return request('POST', `/api/sounds/${encodeURIComponent(name)}/apply`, { sound: null });
      },
      listDisk() { return request('GET', '/api/sounds/_disk/list'); },
      saveDisk(name) { return request('POST', `/api/sounds/_disk/${encodeURIComponent(name)}/save`); },
      loadDisk(name) { return request('POST', `/api/sounds/_disk/${encodeURIComponent(name)}/load`); },
    },

    // -------------------- Effects --------------------

    effects: {
      set(name, value) {
        // Master effects use the master route
        const path = `/api/effects/${name}`;
        return request('POST', path, { value });
      },
    },

    // -------------------- Arpeggiator --------------------

    arp: {
      on() { return request('POST', '/api/arpeggiator/on'); },
      off() { return request('POST', '/api/arpeggiator/off'); },
      rate(v) { return request('POST', '/api/arpeggiator/rate', { rate: v }); },
      gate(v) { return request('POST', '/api/arpeggiator/gate', { gate: v }); },
      style(v) { return request('POST', '/api/arpeggiator/style', { style: v }); },
      octave(v) { return request('POST', '/api/arpeggiator/octave', { octave: v }); },
    },

    // -------------------- SysEx (raw) --------------------

    sysex: {
      dt1(address, payload) { return request('POST', '/api/sysex/dt1', { address, payload }); },
      rq1(address, size) { return request('POST', '/api/sysex/rq1', { address, size }); },
    },

    // -------------------- Patterns --------------------

    patterns: {
      program(track, steps) { return request('POST', '/api/patterns', { track, steps }); },
    },
  };

  window.Api = Api;
})();
