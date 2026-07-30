# Argus Frontend

> **Status:** scaffold only. The backend is built and tested first (this
> milestone); the UI is the next milestone. This README records the plan and the
> decisions so the build can start cleanly.

Two surfaces, deliberately separated:

1. **Operator console** — the day-to-day product. A live **review queue** of
   events ranked by suspicion score, each card showing the evidence frame, the
   VLM's plain-language reason, severity tier, and confirm/dismiss actions
   (those actions are the operator-feedback flywheel from `../docs/02` B1.6).
   Plus per-camera status, live alerts, and threshold tuning.

2. **Marketing / onboarding site** — what a new customer sees before and during
   sign-up: what Argus does, pricing, and a smooth first-run
   ("connect your camera / paste an RTSP URL → see it working in minutes").

## Planned stack (proposed, not yet committed)

- **React + TypeScript + Vite** for the app; **Tailwind** for styling.
- Talks only to the backend HTTP API (`/events`, `/alerts`, `/metrics`,
  `/healthz`, `/control`) — never to pipeline internals. The API is the
  contract, so frontend and backend evolve independently.
- Auth/sign-in is a v1 concern (the backend has no auth yet); until then the
  console runs against a local backend.

## Why it's empty right now

The user asked to **build the backend first**. Shipping a half-built React app
would be noise. When the UI milestone starts, this folder gets the Vite app and
the operator-console components described above, wired to the running backend at
`http://localhost:8080`.

## Design intent

The UI must reinforce **trust** (the core product risk in `../docs/02` B1.3):
confidence *tiers* not a binary alarm, the model's reason always visible so a bad
flag is dismissed in seconds, and one-click feedback that measurably quiets the
system over time.
