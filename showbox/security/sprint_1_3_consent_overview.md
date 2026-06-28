# Sprint 1 + 3 · Consent-Übersicht (SecurityAG)

## Status: PRE-STAGED ✓

Beide DSGVO-relevanten Capabilities sind als **BLOCKED** markiert. Unlock erfolgt erst nach User-Approval des jeweiligen Consent-Flows.

## Sprint 1 — Voice (Cloud-Fallback)

- **Trigger:** Firefox / Gecko-Browser ohne native SpeechRecognition
- **Daten-Flow:** Microphone → TLS → Cloud-Provider
- **Default:** BLOCKED
- **Unlock-Bedingung:** Expliziter Consent-Modal + Provider-Auswahl
- **Provider-Optionen:** Google Cloud / Azure / Self-hosted Whisper
- **Provider-Empfehlung SecurityAG:** **Self-hosted Whisper** (Datenhoheit) — wenn Infrastruktur verfügbar. Sonst Azure (EU-Region, DSGVO-konform).
- **Token-Impact Dialog:** ~80 Tokens
- **Widerruf:** `revokeVoiceCloudConsent()` löscht localStorage + stoppt Stream

## Sprint 3 — Eye-Tracking

- **Trigger:** Sprint-3-Aktivierung (Hands-Free-Drag)
- **Daten-Flow:** Kamera → LOKAL (WebGazer + TF.js) — keine Cloud
- **Default:** BLOCKED — HARD
- **Unlock-Bedingung:** Multi-Step-Consent + granular Toggles + Kalibrierungs-Consent
- **Kill-Switch:** Escape 2x oder expliziter Stop-Button
- **Auto-Disable:** bei CPU > 50% über 3s
- **Widerruf:** `stopEyeTracking()` — stoppt Stream + löscht TF-Modell
- **DSGVO-Patch nötig:** `showbox/datenschutz.md` Abschnitt "Eye-Tracking"

## CoderAG-Handoff

Vor Integration MÜSSEN vorhanden sein:
1. ✅ Consent-Dialoge (Renderer-Pattern `consent_modal_*`)
2. ✅ Capability-Gatekeeper (`voice_cloud_enabled` / `eye_tracking_enabled` Flags)
3. ✅ Kill-Switch-Handler
4. ✅ Audit-Log-Hooks in `soul_audit.db`

## SecurityAG-Bereitschaft

- voice_cloud_consent.json: **READY**
- eye_tracking_consent.json: **READY**
- Provider-Whitelist: ausstehend (User-Approval für Azure-Region oder Self-Hosted-Setup)

## Nächster Schritt

→ User wählt: Sprint 1 / Sprint 3 / beide parallel starten
→ SecurityAG wartet auf `sprint1_start` / `sprint3_start` / `sprint1_3_parallel` Signal