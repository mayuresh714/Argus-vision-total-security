# Argus — Problem Statement & Scope (Foundational)

> **Status:** Draft v0 · Foundational document
> **Last updated:** 2026-07-28
> **Owner:** @mayuresh714
>
> This is the founding document for Argus. It defines *what* problem we are
> solving, *why*, *for whom*, and the *boundaries* of the effort. It does not
> prescribe implementation — that lives in the system design docs
> (`docs/01-...` onward).

---

## 1. One-liner

**Argus watches continuous CCTV footage and raises an alert when it sees
behaviour that looks like theft or other suspicious activity — using
open-source Vision-Language Models (VLMs) to reason about what is happening in
the frame, sampled every _k_ seconds.**

The name is deliberate: *Argus Panoptes*, the hundred-eyed giant of Greek myth
who never slept and never stopped watching.

---

## 2. Background & motivation

Most physical spaces that need security — shops, warehouses, lobbies, parking
lots — already have CCTV cameras. But the footage is almost always used
**reactively**: someone reviews it *after* an incident is reported. A human
cannot realistically watch dozens of feeds continuously, and classical
motion/tripwire alarms are noisy (a swaying tree, a delivery person, a cat all
trip them).

Two things changed recently that make a smarter approach practical:

1. **Open-source VLMs got good and cheap enough.** Models in the Qwen3-VL,
   InternVL3, Llama-4-multimodal, Gemma and Pixtral families can now look at an
   image (or a short clip) and *describe and reason* about the scene in natural
   language — including judging whether an action looks suspicious — at
   deployment costs far below hosted frontier APIs.
2. **Zero-shot works surprisingly well.** Recent research shows VLM-based,
   *label-free* anomaly detection reaching competitive accuracy without any
   task-specific training data — which matters enormously for a project that
   won't have a large labelled theft dataset on day one.

The original idea (captured in my `tech-journey` notes) was simple: instead of
training a bespoke classifier, **try out open-source VLMs as the reasoning
engine** and have them emit an alert every _k_ seconds if something looks off.
Argus is the attempt to turn that idea into a real service.

> _Note: the detailed original notes live in the private `tech-journey` repo,
> which wasn't reachable from the session that drafted this doc. Anything in
> those notes that contradicts or extends this document should be folded in as
> a revision._

---

## 3. Problem statement

> **Given a continuous CCTV video feed, detect — in near-real-time and with
> tolerable false-alarm rates — segments in which a person is likely engaged in
> theft or other suspicious activity, and alert a human with enough context to
> act.**

The hard parts are not "is there a person" (solved) but:

- **Intent is ambiguous.** Picking up an item, concealing it, and walking out
  looks a lot like picking up an item, examining it, and putting it back.
- **Continuous input, bounded compute.** We cannot run a large VLM on every one
  of 25–30 frames per second per camera. We must *sample*.
- **False alarms destroy trust.** An alerting system that cries wolf gets muted
  within a week. Precision matters as much as recall.
- **Privacy and proportionality.** Pointing an AI at people all day carries
  real ethical and legal weight (see §10).

---

## 4. Who it is for

| Stakeholder | What they need from Argus |
|---|---|
| **Small/medium shop owner** | A cheap "second pair of eyes" that pings their phone when something looks like theft, without hiring a guard to watch monitors. |
| **Security operator (multi-camera)** | Triage help — surface the 2% of footage worth looking at, with a clip and a reason. |
| **The person being watched** | *(Not a customer, but a stakeholder.)* Fair, proportionate treatment; not to be flagged for benign behaviour or profiled. |
| **Us (developers)** | A system that is honest about its confidence, easy to tune, and cheap to run. |

The **primary v0 user** is the single-camera shop owner: the simplest,
highest-signal setting.

---

## 5. Goals

### 5.1 Project goals (the north star)

- **G1 — Detect suspicious activity from live footage** with usable
  precision/recall, using VLMs as the reasoning core.
- **G2 — Alert fast enough to matter** (seconds-to-tens-of-seconds, not
  minutes).
- **G3 — Run on commodity hardware / open models** — no dependency on a paid
  frontier API to function.
- **G4 — Be tunable and honest** — every alert carries a confidence and a
  human-readable reason; thresholds are adjustable.
- **G5 — Be extensible** — a clean path from one camera to many, and from
  "theft" to other event types.

### 5.2 Explicit v0 goals

The first milestone is deliberately narrow (detailed in `docs/01`):

- Ingest **one** camera feed (RTSP stream or a video file).
- **Sample a frame every _k_ seconds** and send it to an open-source VLM.
- Get a **structured suspicion assessment** back (score + reason).
- **Raise an alert** (log + notification) when the score crosses a threshold,
  with sensible debouncing so one event ≠ ten alerts.
- Be a single, runnable service with config, logs, and a saved event record.

---

## 6. Non-goals (for now)

Being explicit about what we are **not** doing keeps scope honest.

- ❌ **Not** a multi-camera fleet / NVR platform in v0 (that's a later phase).
- ❌ **Not** person re-identification, face recognition, or identity tracking.
  Argus judges *behaviour in frame*, not *who* someone is.
- ❌ **Not** an autonomous enforcement system. Argus **alerts a human**; it
  never locks doors, detains, or accuses.
- ❌ **Not** a trained-from-scratch bespoke model effort (yet). We start by
  leveraging pretrained open VLMs; fine-tuning is a possible later optimisation.
- ❌ **Not** promising courtroom-grade evidence or legal proof of intent.
- ❌ **Not** guaranteeing real-time per-frame analysis — the _k_-second sampling
  cadence is a core design assumption, not a limitation to be apologised for.

---

## 7. Core hypothesis & approach

**Hypothesis:** *A pretrained open-source VLM, prompted well and fed a frame (or
short clip) every _k_ seconds, can flag suspicious activity with high enough
precision to be useful, without any task-specific training.*

The bet is on **sampling + reasoning** rather than **dense tracking +
classification**:

```
CCTV feed ──► sample 1 frame / k seconds ──► VLM("is this suspicious? why?")
                                                  │
                                                  ▼
                                     structured {score, reason, tags}
                                                  │
                                                  ▼
                              threshold + debounce ──► alert + saved clip
```

### Why VLM instead of classical CV?

| Approach | Pro | Con |
|---|---|---|
| Motion / tripwire | Cheap, instant | Extremely noisy, no notion of *intent* |
| Object detection (YOLO) | Fast, mature | Knows "person + bag", not "concealing an item" |
| Pose-based classifiers | Good for specific gaits/actions | Needs labelled data; brittle across venues |
| **VLM (our bet)** | **Zero-shot, reasons about context, explains itself in words, generalises across venues** | **Slower, heavier, can hallucinate, needs prompt/threshold tuning** |

The VLM's *self-explanation* ("person placed item into jacket, then walked past
the till") is a first-class feature: it makes alerts triageable and the system
debuggable. A hybrid (cheap detector as a gate, VLM as the reasoner) is an
obvious future optimisation, noted in the roadmap.

### The role of _k_

_k_ (seconds between sampled frames) is the central tuning knob trading **cost
vs. responsiveness vs. miss-rate**:

- Small _k_ (e.g. 1–2 s): more responsive, more likely to catch a brief action,
  more VLM calls → more cost.
- Large _k_ (e.g. 10–15 s): cheap, but a quick grab-and-go between samples can
  slip through.

v0 makes _k_ configurable and treats finding good defaults as an explicit
experiment.

---

## 8. Success criteria & metrics

We can't call this working on vibes. Target signals:

**Detection quality**
- **Precision** (of raised alerts, what fraction are truly suspicious) —
  the metric we care about *most*, because low precision kills adoption.
- **Recall** (of true incidents, what fraction we alerted on).
- **False alarms per hour** per camera under normal traffic — the practical
  "is this annoying" number.

**Timeliness**
- **Alert latency**: seconds from the suspicious act to the notification.

**Operability / cost**
- **VLM cost per camera-hour** (compute or API $).
- **Throughput**: cameras a single GPU/box can serve at a given _k_.

**v0 bar (intentionally modest):** on a handful of test clips (staged + public
shoplifting datasets such as DCSASS / UCF-Crime-style footage), demonstrate the
end-to-end loop firing correct alerts on obvious theft, with a *characterised*
(not necessarily low yet) false-alarm rate, and per-alert reasons that a human
agrees with. v0 proves the pipeline; v1 optimises the numbers.

---

## 9. Constraints & assumptions

- **Compute:** assume access to one machine with a modern consumer/prosumer GPU
  (or a modest cloud GPU). Quantised open VLMs must fit.
- **Camera:** assume a reachable RTSP stream or recorded file; fixed-ish
  mounting; usable (not pitch-black) lighting. Night-vision/IR is out of v0.
- **Latency budget:** tens of seconds end-to-end is acceptable for v0.
- **No labelled theft dataset** of our own at the start — hence the zero-shot
  VLM bet.
- **Single time zone / single site** operationally for v0.
- **Model availability:** open-weight VLMs remain downloadable and runnable
  locally (Qwen3-VL / InternVL3 / Gemma-multimodal class).

---

## 10. Ethics, privacy & safety

This project points AI at people, so this section is a *requirement*, not a
footnote.

- **Human-in-the-loop, always.** Argus raises alerts for a person to judge. It
  does not accuse, detain, or take automated action.
- **Behaviour, not identity.** No face recognition or re-identification in
  scope. We evaluate *what is happening*, not *who* it is.
- **Bias awareness.** VLMs can carry demographic biases. Suspicion output must
  be monitored so the system doesn't systematically over-flag any group; this
  is a tracked risk, not an afterthought.
- **Data minimisation.** Keep sampled frames / clips only as long as needed for
  the alert workflow; make retention configurable and default-short.
- **Transparency.** Every alert stores the frame(s) and the model's stated
  reason, so decisions are auditable and contestable.
- **Legal siting.** Deployers are responsible for lawful camera placement,
  signage, and consent where required. Argus is a tool; lawful use is the
  operator's duty.
- **Fail toward caution.** When uncertain, prefer "flag for human review" over
  silent high-confidence judgements presented as fact.

---

## 11. Key risks & open questions

| # | Risk / question | Why it matters | Current stance |
|---|---|---|---|
| R1 | VLM false positives too high | Kills trust/adoption | Tune threshold + debounce; measure precision first |
| R2 | Missed events between samples | Defeats the purpose | Tune _k_; consider motion-gated bursty sampling |
| R3 | VLM latency/cost per call | Limits cameras/box | Use quantised models; batch; pick smallest model that works |
| R4 | Hallucinated reasons | Misleads operators | Require structured output; log raw model text; calibrate |
| R5 | Single-frame lacks motion context | Theft is temporal | v0 = single frame; evaluate short-clip / frame-stack input early |
| R6 | Bias / fairness | Ethical + reputational | Monitor per-group flag rates; §10 |
| Q1 | Best _k_ default? | Core knob | Experiment in v0 |
| Q2 | Single frame vs short clip vs frame-stack? | Accuracy vs cost | Design v0 to swap the "unit of analysis" |
| Q3 | Which open VLM is the sweet spot? | Cost/accuracy | Benchmark 2–3 candidates against test clips |

---

## 12. Roadmap (phases)

- **Phase 0 — Foundation (this doc).** Problem, scope, success criteria. ✅
- **Phase 1 — v0 single-camera service** (`docs/01`). One feed → sample every
  _k_ s → VLM → threshold → alert. Prove the loop end-to-end.
- **Phase 2 — Quality.** Short-clip / temporal context, motion-gated sampling,
  prompt & threshold tuning, precision/recall measurement on real clips,
  model bake-off.
- **Phase 3 — Scale.** Multiple cameras, worker pool, an event dashboard,
  retention policies.
- **Phase 4 — Optimise.** Hybrid cheap-detector gate + VLM reasoner; optional
  fine-tuning; edge deployment.

---

## 13. Glossary

- **VLM (Vision-Language Model):** a model that takes images (± text) and
  produces text — here, a suspicion judgement and its reasoning.
- **_k_ / sampling interval:** seconds between frames sent to the VLM.
- **Unit of analysis:** what one VLM call sees — a single frame in v0; possibly
  a short clip or frame-stack later.
- **Alert:** a notified, human-facing event raised when suspicion crosses
  threshold, carrying score + reason + evidence frame(s).
- **Event:** any scored observation Argus records (may or may not become an
  alert).
- **Debounce / cooldown:** logic preventing one real incident from firing many
  repeated alerts.
- **Zero-shot:** using a pretrained model on our task with no task-specific
  training.

---

## 14. References & prior art

- Open-source VLM landscape 2026 — BentoML guide:
  <https://www.bentoml.com/blog/multimodal-ai-a-guide-to-open-source-vision-language-models>
- Open-source VLM survey (2026): <https://blog.overshoot.ai/blog/vlm-survey-2026>
- *Are Multimodal LLMs Ready for Surveillance? A Reality Check on Zero-Shot
  Anomaly Detection in the Wild* — <https://arxiv.org/pdf/2603.04727>
- *Zero-Shot Retail Theft Detection via Orchestrated Vision Models* —
  <https://arxiv.org/pdf/2604.14846>
- *Exploring Pose-Based Anomaly Detection for Retail Security* —
  <https://arxiv.org/pdf/2501.06591>
- Top anomaly-detection models for video surveillance (2026), Forasoft —
  <https://www.forasoft.com/blog/article/anomaly-detection-models-video-surveillance>

---

*Next: `docs/01-system-design-v0-single-camera.md` — the version-0 design for
the single-camera footage analysis service.*
