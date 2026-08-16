# ⚙️ Argus Backend

Express API + Socket.IO. Runs the scan pipeline and serves cameras, alerts, and auth.

**Live:** `https://argus-backend-uq4n.onrender.com`

## Run

```bash
npm install
cp .env.example .env
npm run dev   # http://localhost:4000
```

Demo login: `operator@argus.demo` / `argus123` (seeded on boot).

## API

- `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`
- `GET/POST /api/cameras`, `GET/PATCH/DELETE /api/cameras/:id`, `POST /api/cameras/:id/toggle`
- `GET /api/alerts`, `GET /api/alerts/:id`, `PATCH /api/alerts/:id` (acknowledge/dismiss)

Socket.IO events: `frame:sampled`, `scan:tier`, `frame:analyzed`, `alert:new`.

## The scan pipeline

`src/services/scanPipeline.js` runs three tiers per sampled frame, each one only firing if the last one wasn't confident:

1. **Tier 1 — fast scan** (`services/models/tier1Heuristic.js`) — cheap, runs on every frame.
2. **Tier 2 — local AI model** (`services/models/tier2LocalVlm.js`) — only runs if Tier 1 is unsure.
3. **Tier 3 — deep analysis** (`services/models/tier3Sophisticated.js`) — only runs if Tier 2 is still unsure.

Point `TIER2_ENDPOINT` / `TIER3_ENDPOINT` at your own model server (POST an image + prompt, expect `{ score, confidence, reason, tags }` back) and it's used automatically. Without one set, each tier falls back to a built-in simulator so the app runs end-to-end with nothing else attached.

An alert fires when the final score crosses the per-camera `alertThreshold` (adjustable in Settings) and pushes live over Socket.IO.
