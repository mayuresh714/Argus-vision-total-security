# Argus Backend (v0 — single camera)

Python implementation of the single-camera footage-analysis service designed in
[`../docs/01-system-design-v0-single-camera.md`](../docs/01-system-design-v0-single-camera.md).

It samples one camera every _k_ seconds, asks a Vision-Language Model whether the
scene looks suspicious, and raises a debounced, explainable alert when it does.

## Why Python (and the edge note)

Python is the fastest path to a correct, well-tested v0 and has the best
CV/VLM ecosystem. The core is deliberately dependency-light — the pipeline,
decision logic, storage, and alerting import **nothing** heavier than the stdlib
(OpenCV is an *optional* extra used only by the real file/RTSP sources). That
keeps the door open for on-device deployment: the expensive always-on "Stage-0"
gating (motion/person) can later be moved to a native/compiled module or an edge
box **without touching the pipeline**, because every collaborator sits behind an
interface (see the design decisions in `../docs/02`).

## Layout & design

```
src/argus/
  domain/        pure value objects (Frame, AnalysisUnit, SuspicionResult, Event, Alert)
  sources/       FrameSource: FakeSource (core) + FileVideoSource/RtspSource (OpenCV)
  vlm/           VlmBackend Strategy: MockVlmBackend + OpenAiCompatibleVlmBackend, prompt, parser
  decision/      DecisionEngine: severity tiers, consecutive-N, hysteresis, cooldown
  alerting/      Notifier Strategy (console/file/webhook) + AlertManager (fan-out, isolation)
  storage/       Repository (in-memory / SQLite) + EvidenceWriter
  pipeline/      LatestSlot (drop-oldest) + Sampler + InferenceWorker + ArgusService (composition root)
  api/           FastAPI: /healthz /metrics /events /alerts /control
```

Design principles applied (not decoration):

- **SOLID.** Every layer depends on an *interface*, not a concrete class; the
  only place that knows concrete types is the composition root
  (`pipeline/service.py`). Adding a new VLM/notifier/source/store is a new class
  + one factory line — no edits to the pipeline. Time (`Clock`) and HTTP
  (`Transport`) are injected, which is what makes cooldown/network behaviour
  deterministically testable.
- **Patterns.** Strategy (VlmBackend, Notifier, FrameSource, Repository),
  Factory (`create_*` + `build_service`), Repository (storage), and a
  drop-oldest bounded buffer (`LatestSlot`) that encodes the "freshness over
  backlog" rule from the design.
- **Single Responsibility.** Sampler *schedules*, sources *decode*, the worker
  *reasons + decides*, the manager *delivers*. The Sampler/Worker each split a
  testable `*_once`/`process` method out of their thread loop.

## Quickstart

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"          # core + test deps
pip install -r requirements-video.txt   # only if using real file/rtsp sources

# Run the tests
pytest

# Run the service with defaults (fake source + mock VLM — no camera needed)
argus                            # serves the API on :8080
# or point at a config:
cp config.example.yaml config.yaml   # edit source/uri/model/thresholds
argus --config config.yaml
```

Then hit the API:

```bash
curl localhost:8080/healthz
curl localhost:8080/metrics
curl localhost:8080/alerts
curl localhost:8080/events
```

## Using a real VLM

Point `vlm.backend: openai_compatible` at any OpenAI-style vision endpoint — a
local open model served by **vLLM / Ollama** (the intended production workhorse,
see `../docs/02` B2) or a hosted frontier model behind a proxy. The API key is
read from the env var named in `vlm.api_key_env`, never stored in config:

```bash
export ARGUS_VLM_API_KEY=...   # if your endpoint needs auth
```

## Testing

`pytest` runs the full suite (unit + an end-to-end **scene-replay** acceptance
test that pushes a scripted "normal → theft → normal" sequence through the real
pipeline and asserts alerts fire, debounced). No camera, network, or GPU
required — everything heavy is behind an injected fake.

## Status / not yet built (Phase 2+, see `../docs/00` roadmap)

Short-clip / N-frame temporal analysis, motion-gated bursty sampling, the
Stage-0 cheap detector, retention pruning job, and multi-camera fan-out. The
interfaces here (`AnalysisUnit`, `FrameSource`, `VlmBackend`) were shaped so
those slot in without a rewrite.
