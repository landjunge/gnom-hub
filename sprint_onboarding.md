# 🚀 Sprint-Onboarding-Snippet

> **Stand:** Sprint-Routing finalisiert · Pipeline warm · 6 Memory-Fakten persistiert
> **Audience:** Alle Agents + neue Sprint-Picks

---

## 🎯 Sprint-Map (Live)

| Sprint | Topic | Status | Quelle-Triangel |
|--------|-------|--------|-----------------|
| **1** | Web Speech API | 🟢 **AKTIV** | MDN · CanIUse · W3C Draft |
| **2** | View Transitions | 🏁 **STANDBY** | MDN (nachschiebbar) |
| **3** | Eye-Tracking / WebGazer | 🟢 **AKTIV** | WebGazer.js · MediaPipe · W3C WebXR |

**Doppelschiene läuft:** Sprint 1 + 3 parallel. Sprint 2 ist auf Standby — kein Block, nur kein Cold-Start.

---

## 📚 Memory-Fakten (persistiert in `soul_memory.db`)

### 1. Speech API Browser-Support
- **Chrome / Edge:** ✅ nativ (`SpeechRecognition` + `SpeechSynthesis`)
- **Safari:** ⚠️ partial — nur `SpeechSynthesis`, Recognition fehlt
- **Firefox:** 🚩 **nur via Flag** (`media.webspeech.recognition.enable`)
- **Mobile-Safari:** ⚠️ stark eingeschränkt, oft keine Recognition

### 2. WebGazer Caveat (Kamera-Permission-UX)
- **Hard-Requirement:** Expliziter Camera-Permission-Flow vor `webgazer.setGazeListener()`
- **UX-Pattern:** Pre-Prompt → Permission-Request → Loading-State → Calibration-Step
- **Fallout:** Kein Permission = kein Gaze-Tracking = Feature-Disabled-UI

### 3. Quellen-Triangel Sprint 1
- MDN (Primary Spec-Doku)
- CanIUse (Compat-Heatmap)
- W3C Draft (Standards-Status)

### 4. Quellen-Triangel Sprint 3
- WebGazer.js (Library)
- MediaPipe (Alternative / Benchmark)
- W3C WebXR (Standards-Pfad)

### 5. Pipeline-Health
- **177 Jobs** historisch · **99% Completion**
- SmartRouter darf voll ziehen — kein Cold-Start
- ResearcherAG bleibt warm für Sprint-2-Nachschub

### 6. Memory-Layer
- `soul_memory.db` enthält Sprint-Topics + Caveats
- Nachschlagbar für Sprint-Retros
- Provenienz pro Fakt dokumentiert

---

## ⚠️ Caveats an Implementer

```
🚩 Firefox Speech API   → Flag-Pfad dokumentieren
📸 WebGazer Camera-UX   → Permission-Flow Pflicht
🏁 Sprint 2 Standby     → kein paralleler Cold-Start
```

---

## 🔗 Routing-Quickref

| Agent | Sprint 1 | Sprint 3 |
|-------|----------|----------|
| **CoderAG** | Speech-API-Compat-Shim + Firefox-Flag-Detect | WebGazer-Init + Permission-UX |
| **EditorAG** | Token-System-Review, Copy-Schliff | UX-Pattern-Konsistenz |
| **ResearcherAG** | MDN-Updates scannen | MediaPipe-Benchmarks |
| **WriterAG** | API-Doc-Snippets | Onboarding-Update bei Spec-Changes |
| **SoulAG** | Sprint-Synthese | Sprint-Synthese |
| **GeneralAG** | Sprint-Routing | Sprint-Routing |

---

## ▶️ Start-Checklist

- [ ] Sprint-1-Compat-Map an CoderAG übergeben
- [ ] Sprint-3-Kamera-UX-Flow an CoderAG übergeben
- [ ] ResearcherAG-Scanner läuft warm
- [ ] EditorAG-Stilkontrolle auf Standby
- [ ] Memory-Sync nach jedem Sprint-Retro

---

*Snippet wartet im Hub. Bei Sprint-Start: Snippet reviewen, Caveats an Implementer durchreichen, loslegen.*