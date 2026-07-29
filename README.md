# Argus — Vision Total Security

> *Argus Panoptes, the hundred-eyed watcher who never slept.*

Argus watches continuous CCTV footage and raises an alert when it sees behaviour
that looks like **theft or other suspicious activity** — using open-source
**Vision-Language Models (VLMs)** to reason about what's happening in the frame,
sampled every _k_ seconds.

Instead of training a bespoke classifier, the bet is to use pretrained
open-source VLMs (Qwen3-VL / InternVL3 / Gemma-multimodal class) as a
**zero-shot reasoning engine**: sample a frame, ask "does this look suspicious,
and why?", and alert a human — with a confidence score and a plain-language
reason — when it crosses a threshold.

## Status

Early / foundational. This repo currently holds the founding documents; the v0
service is a design proposal, not yet implemented.

## Documentation

- [`docs/00-problem-and-scope.md`](./docs/00-problem-and-scope.md) — **the
  founding document**: problem, scope, goals/non-goals, the VLM approach,
  success metrics, ethics & privacy, risks, and roadmap.
- [`docs/01-system-design-v0-single-camera.md`](./docs/01-system-design-v0-single-camera.md)
  — **version-0 system design** for the single-camera footage analysis service:
  the sample-every-_k_-seconds loop, components, data model, prompt design,
  tech choices, and failure handling.
- [`docs/02-hard-questions-strategy-and-answers.md`](./docs/02-hard-questions-strategy-and-answers.md)
  — **the hard questions**, collected then answered like a founder/engineer
  building for millions of cameras: speed↔accuracy, false alarms & trust, image
  vs video, which VLM (Claude/Gemini/GPT vs open-source) and what it really
  costs per camera, scaling architecture, integrations, revenue model, market
  size, and the competitive landscape.

## Core idea in one diagram

```
CCTV feed ──► sample 1 frame / k seconds ──► VLM("is this suspicious? why?")
                                                  │
                                                  ▼
                                     structured {score, reason, tags}
                                                  │
                                                  ▼
                              threshold + debounce ──► alert + saved clip
```

## Principles

- **Human-in-the-loop** — Argus alerts a person; it never accuses, detains, or
  acts autonomously.
- **Behaviour, not identity** — no face recognition or re-identification.
- **Honest & tunable** — every alert carries a confidence and a reason;
  thresholds and the sampling interval _k_ are configurable.
- **Open models, commodity hardware** — no dependency on a paid frontier API to
  function.

See the [foundation doc](./docs/00-problem-and-scope.md) for the full ethics,
privacy, and scope discussion.
