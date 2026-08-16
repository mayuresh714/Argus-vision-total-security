# Argus Frontend (web + mobile-responsive)

React + Vite single-page app. Web-first, fully responsive down to mobile
widths (bottom tab bar under 860px, sidebar nav above), so the same codebase
works as the phone UI too. Talks to the backend over REST + a Socket.IO
stream for live scan/alert events.

## Screens

- **Login** — email/password auth (demo: `operator@argus.demo` / `argus123`)
- **Dashboard** — camera status, alert counters, recent alerts
- **Cameras** — list/add/pause/delete cameras
- **Camera Live** — live three-tier scan feed for one camera + its recent alerts
- **Alerts** — filterable alert feed (new/acknowledged/dismissed)
- **Alert Detail** — evidence, reason, full tier escalation trace, acknowledge/dismiss
- **Settings** — account info, per-camera sampling interval & alert threshold

## Run

```bash
npm install
npm run dev   # http://localhost:5173, proxies /api and /socket.io to :4000
```

Requires the backend running on port 4000 (see `../backend`).
