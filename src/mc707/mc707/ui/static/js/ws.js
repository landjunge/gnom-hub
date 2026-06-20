/* =================================================================
   ws.js — WebSocket client for the mc707 WebUI backend
   =================================================================
   - Auto-reconnect with exponential backoff (cap 8s)
   - Replays the active subscription set after each reconnect
   - Dispatches every incoming event to ``onEvent(type, data)``
   - Exposes ping() for keepalive
   ================================================================= */

(function () {
  'use strict';

  const RECONNECT_BASE_MS = 500;
  const RECONNECT_MAX_MS = 8000;

  class MC707WebSocket {
    constructor(path) {
      this.path = path || this._defaultPath();
      this.ws = null;
      this.connected = false;
      this.reconnectAttempts = 0;
      this.reconnectTimer = null;
      this.subscriptions = new Set();
      this.lastEvent = null;
      this._eventHandler = null;
      this._stateChangeHandler = null;
      this._closed = false;
    }

    _defaultPath() {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${proto}//${window.location.host}/ws`;
    }

    /**
     * Set the event handler. ``handler(type, data)`` is called for every
     * server-pushed event. Errors should be swallowed by the handler.
     */
    onEvent(handler) {
      this._eventHandler = handler;
    }

    onStateChange(handler) {
      this._stateChangeHandler = handler;
    }

    _setConnected(value) {
      if (this.connected !== value) {
        this.connected = value;
        if (this._stateChangeHandler) this._stateChangeHandler(value);
      }
    }

    connect() {
      if (this._closed) return;
      try {
        this.ws = new WebSocket(this.path);
      } catch (e) {
        console.error('WebSocket construct failed', e);
        this._scheduleReconnect();
        return;
      }

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this._setConnected(true);
        // Replay subscriptions
        if (this.subscriptions.size > 0) {
          this._send({ action: 'subscribe', events: [...this.subscriptions] });
        }
        // Keepalive ping every 25s
        this._pingTimer = setInterval(() => this.ping(), 25000);
      };

      this.ws.onmessage = (evt) => {
        let msg;
        try { msg = JSON.parse(evt.data); } catch (_) { return; }
        const type = msg.type;
        const data = msg.data || {};
        this.lastEvent = `${type} ${new Date().toLocaleTimeString()}`;
        if (this._eventHandler) {
          try { this._eventHandler(type, data); } catch (e) { console.error(e); }
        }
      };

      this.ws.onerror = (evt) => {
        console.warn('WebSocket error', evt);
      };

      this.ws.onclose = () => {
        this._setConnected(false);
        if (this._pingTimer) { clearInterval(this._pingTimer); this._pingTimer = null; }
        this._scheduleReconnect();
      };
    }

    _send(obj) {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
      this.ws.send(JSON.stringify(obj));
      return true;
    }

    _scheduleReconnect() {
      if (this._closed) return;
      if (this.reconnectTimer) return;
      this.reconnectAttempts += 1;
      const delay = Math.min(
        RECONNECT_MAX_MS,
        RECONNECT_BASE_MS * Math.pow(1.5, this.reconnectAttempts - 1)
      );
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, delay);
    }

    subscribe(events) {
      events.forEach(e => this.subscriptions.add(e));
      this._send({ action: 'subscribe', events });
    }

    unsubscribe(events) {
      events.forEach(e => this.subscriptions.delete(e));
      this._send({ action: 'unsubscribe', events });
    }

    ping() {
      this._send({ action: 'ping' });
    }

    close() {
      this._closed = true;
      if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
      if (this._pingTimer) { clearInterval(this._pingTimer); this._pingTimer = null; }
      if (this.ws) {
        try { this.ws.close(); } catch (_) {}
      }
    }
  }

  window.MC707WebSocket = MC707WebSocket;
})();
