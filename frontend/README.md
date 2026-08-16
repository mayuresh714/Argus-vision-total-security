# 📱 Argus Frontend

React + Vite. Web-first, fully responsive — same codebase serves desktop (sidebar nav) and mobile (bottom tab bar).

**Live:** `https://argus-vision-total-security.vercel.app`

## Screens

- **Login**
- **Dashboard** — camera status, alert counts, recent alerts
- **Cameras** — add, pause, delete
- **Camera Live** — real-time scan feed for one camera
- **Alerts** — filterable feed
- **Alert Detail** — evidence, reason, full escalation trace, acknowledge/dismiss
- **Settings** — account info, per-camera sampling interval & alert threshold

## Run

```bash
npm install
npm run dev   # http://localhost:5173, proxies /api and /socket.io to :4000
```

Needs the backend running (see `../backend`). To point at a deployed backend instead, set `VITE_API_URL` in a `.env` file.
