# Argus Backend

Node.js/Express REST API + Socket.IO, kept fully separate from the frontend.

## Run

```bash
npm install
cp .env.example .env
npm run dev   # http://localhost:4000
```

Demo login: `operator@argus.demo` / `argus123` (seeded on boot, in-memory store).

## API

- `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`
- `GET/POST /api/cameras`, `GET/PATCH/DELETE /api/cameras/:id`, `POST /api/cameras/:id/toggle`
- `GET /api/alerts`, `GET /api/alerts/:id`, `PATCH /api/alerts/:id` (ack/dismiss)

Socket.IO events: `frame:sampled`, `scan:tier`, `frame:analyzed`, `alert:new`.

## Three-tier scan pipeline

`src/services/scanPipeline.js` orchestrates escalation per sampled frame:

1. **Tier 1 — fast local scan** (`services/models/tier1Heuristic.js`): cheap
   heuristic, runs on every frame. Only escalates when its score crosses
   `TIER1_SUSPICION_THRESHOLD`.
2. **Tier 2 — local VLM** (`services/models/tier2LocalVlm.js`): on-device VLM
   (e.g. Qwen3-VL/InternVL3 class). Runs only when Tier 1 is unsure. Escalates
   further when its confidence is below `TIER2_CONFIDENCE_ESCALATE_BELOW`.
3. **Tier 3 — sophisticated model** (`services/models/tier3Sophisticated.js`):
   the expensive, most-accurate path. Runs only when Tier 2 is still unsure.

Each model file is a pluggable interface: point `TIER2_ENDPOINT` /
`TIER3_ENDPOINT` at a real model server (POST image + prompt, expect
`{ score, confidence, reason, tags }`) and it's used automatically; otherwise
each tier falls back to a built-in mock reasoner so the whole app runs
end-to-end without any model server attached.

An alert is created when the final tier's score crosses the per-camera
`alertThreshold` (tunable in Settings), and pushed live over Socket.IO.
