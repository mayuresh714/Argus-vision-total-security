# 👁️ Argus

**AI security camera monitoring that tells you *why* something looks wrong — not just that it does.**

Argus watches your cameras, scores every frame for suspicious behavior, and only pings you when it's actually worth a look — with a plain-language reason attached.

🔗 **Live demo:** [argus-vision-total-security.vercel.app](https://argus-vision-total-security.vercel.app)
Demo login: `operator@argus.demo` / `argus123`

---

## ✨ Features

- 📊 **Dashboard** — camera status and recent alerts at a glance
- 📷 **Camera management** — add, pause, tune, or remove cameras
- 🔴 **Live scan feed** — watch the AI reason about each frame in real time
- 🚨 **Alerts** — filterable feed with full evidence and escalation trace
- ✅ **Acknowledge / dismiss** — mark alerts reviewed or false-positive
- ⚙️ **Per-camera tuning** — sample rate and alert sensitivity, no redeploy needed
- 📱 **Works on your phone** — same app, responsive from day one

## 🧠 How the AI pipeline works

Most frames are boring. Argus is built around that: cheap checks run constantly, expensive ones only run when something looks off.

```
Every sampled frame
      │
      ▼
  Tier 1 — fast scan          (runs on every frame)
      │  unsure?
      ▼
  Tier 2 — local AI model     (only runs if Tier 1 is unsure)
      │  still unsure?
      ▼
  Tier 3 — deep analysis      (only runs if Tier 2 is still unsure)
      │
      ▼
  Alert, with a reason
```

Tier 2 and Tier 3 are pluggable — point them at your own model server (local or cloud) and the pipeline uses it automatically. Without one configured, Argus falls back to a built-in simulator so the whole app works out of the box.

## 🛠️ Stack

| | |
|---|---|
| **Frontend** | React + Vite, deployed on Vercel |
| **Backend** | Node.js + Express + Socket.IO, deployed on Render |
| **Realtime** | WebSockets — alerts and scan events push live, no polling |

Frontend and backend are separate codebases that talk over REST + WebSocket — swap either one out independently.

## 🚀 Run it locally

```bash
# backend
cd backend && npm install && cp .env.example .env && npm run dev   # → :4000

# frontend (new terminal)
cd frontend && npm install && npm run dev                          # → :5173
```

Open `http://localhost:5173` and log in with the demo account above.

## 📂 Structure

```
backend/    Express API + Socket.IO + the scan pipeline
frontend/   React app (web + mobile-responsive)
```

See `backend/README.md` and `frontend/README.md` for details on each side.
