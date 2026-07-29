# Argus — Hard Questions: Technical, Product & Business Strategy

> **Status:** Draft v0 · Strategy / decision document
> **Last updated:** 2026-07-28
> **Owner:** @mayuresh714
> **Prereq reading:** [`00-problem-and-scope.md`](./00-problem-and-scope.md),
> [`01-system-design-v0-single-camera.md`](./01-system-design-v0-single-camera.md)

This document does two things:

1. **Part A — the Question Bank.** Collects *every* hard question worth asking
   about turning Argus from "a VLM on one camera" into "a system that could run
   on millions of CCTVs" — technical, product, integration, and business.
2. **Part B — the Answers.** Works through them one at a time, reasoning like a
   founder / engineer / operator, not just a coder. Answers are **opinionated
   and current as of mid-2026**, and each is explicitly marked as a decision, a
   hypothesis to test, or an open bet.

Numbers here (market sizes, API prices, cost math) are grounded in cited 2026
sources at the end. Treat the dollar figures as order-of-magnitude, not quotes.

---

# Part A — The Question Bank

### A1. Detection quality (the core technical problem)
- **Q1.1** Speed vs accuracy: bigger/slower models are more accurate but can't
  keep up with live feeds. Where's the trade-off, and per what unit?
- **Q1.2** Image vs video: is a single frame enough, or do we need short clips /
  frame-stacks to capture *intent* (theft is a temporal act)?
- **Q1.3** False alarms: how do we get precision high enough that operators keep
  the system on? (A noisy alarm gets muted in a week — the #1 killer.)
- **Q1.4** How do we capture temporal context / intent without exploding cost?
- **Q1.5** Hard visual conditions: night/IR, occlusion, crowds, glare, camera
  angle, low resolution, weather. How much do these degrade a VLM?
- **Q1.6** How do we measure any of this without a big labelled theft dataset?
- **Q1.7** Hallucination: VLMs invent confident, wrong reasons. How do we keep
  the "reason" trustworthy?
- **Q1.8** Adversarial reality: people learn what trips the system and adapt.

### A2. Model choice & cost
- **Q2.1** Which VLM — Claude, Gemini, GPT, or open-source (Qwen3-VL / InternVL3
  / Gemma)? Frontier APIs are "expensive… or maybe not, I don't know."
- **Q2.2** What does it *actually* cost per camera per month at each option,
  naively? (Spoiler: naive is unaffordable.)
- **Q2.3** Self-hosted open model vs hosted API: which wins, and at what scale
  does the answer flip?
- **Q2.4** Where does inference run — edge (on/near camera), regional, or cloud?
- **Q2.5** Do we ever need to fine-tune, or is zero-shot + good prompting enough?

### A3. Scale & architecture (millions of cameras)
- **Q3.1** Single user with **multiple cameras** — what changes vs one camera?
- **Q3.2** How do we go from 1 → 100 → 1,000,000 cameras without cost scaling
  linearly with a frontier API bill?
- **Q3.3** Bandwidth & storage: streaming millions of feeds to the cloud is
  insane. What actually moves over the network?
- **Q3.4** How do we keep per-camera cost low enough to fit a viable price?
- **Q3.5** Multi-tenancy, isolation, and reliability at that scale.

### A4. Integration with existing setups
- **Q4.1** Do customers already have cameras? How do we plug into *installed*
  hardware (RTSP / ONVIF / existing NVRs / VMS like Milestone, Genetec, Meraki)?
- **Q4.2** Software-overlay ("bring your own camera") vs full-stack (sell the
  camera too, like Verkada). Which model?
- **Q4.3** How do alerts reach the human — app, SMS, existing SOC / VMS, phone?
- **Q4.4** On-prem / air-gapped customers who won't send video to a cloud.

### A5. Business, market & competition
- **Q5.1** How big is the market, really, and which slice is winnable?
- **Q5.2** Who are the existing players and how do we not get crushed by them?
- **Q5.3** What's the revenue model — per camera, per alert, per seat, tiered?
- **Q5.4** What's the moat? VLMs are a commodity; anyone can prompt one.
- **Q5.5** Go-to-market: who's the wedge customer and why do they switch?
- **Q5.6** Unit economics — can we make money per camera at a price people pay?

### A6. Legal, ethical & trust at scale
- **Q6.1** Liability: what happens when Argus is wrong (false accusation, or a
  missed crime someone relied on us for)?
- **Q6.2** Bias & fairness across demographics, at scale, in the press.
- **Q6.3** Privacy law (GDPR, BIPA, state laws, India's DPDP) and consent.
- **Q6.4** Human-in-the-loop as product *and* legal posture.

---

# Part B — Answers, one at a time

Legend: **[DECISION]** we're committing · **[HYPOTHESIS]** believe, must test ·
**[BET]** strategic, unproven · **[WATCH]** risk to monitor.

---

## B1. Detection quality

### Q1.1 — Speed vs accuracy trade-off
**[DECISION] Don't frame it as one global trade-off; frame it as a *cascade*.**

The mistake is picking one model to do everything on every frame. Instead:

```
cheap always-on filter  →  small VLM on "interesting" frames  →  big VLM/human only on borderline high-stakes cases
   (motion/person)            (score + reason)                     (confirm before alerting)
```

- **Stage 0 (free, per-frame):** motion detection + a lightweight person
  detector (YOLO-class). ~99% of CCTV footage is boring (empty aisle, staff
  restocking). Never spend a VLM token on it.
- **Stage 1 (cheap VLM, on interesting frames only):** an 8B-class open VLM
  gives score + reason. This is the workhorse.
- **Stage 2 (expensive, rare):** only when Stage 1 is *borderline* and stakes
  are high, escalate to a bigger model or a short clip or a human.

This turns "speed vs accuracy" into "spend accuracy budget only where it
matters." It's also the single biggest cost lever (see B2). Accuracy is chosen
*per stage*, latency stays bounded because 99% of frames never reach a VLM.

### Q1.2 — Image vs video (the debate you named)
**[HYPOTHESIS → likely DECISION] Start single-frame, move to short-clip fast;
never go full dense-video.**

- A **single frame** often *is* enough for concealment-style theft ("item going
  into jacket" is visible in one frame) and is the cheapest possible unit. It's
  the right *v0* choice — proves the loop.
- But intent is **temporal**: "picked up → concealed → walked out past till" is
  a sequence. A single frame can't distinguish "putting item in bag to buy" from
  "concealing to steal." So a **short clip or a stack of ~4–8 sampled frames**
  (e.g. one every 0.5–1s over a few seconds) fed to a video-capable VLM is the
  real answer for accuracy.
- **Full-motion, every-frame video** into a VLM is off the table — it's the most
  expensive option and mostly redundant. The sweet spot is **event-triggered
  short clips**: Stage 0 detects motion/person, then we hand the VLM a *short
  burst*, not a lone frame and not a continuous stream.

**Net:** the *unit of analysis* is a tunable dial from 1 frame → N-frame stack →
short clip. Argus's design (the `AnalysisUnit` interface in `docs/01`) is built
to slide along it. Bet: **N-frame stacks are the 80/20** — most of the temporal
signal, a fraction of video cost.

### Q1.3 — False alarms killing trust (the #1 product risk)
**[DECISION] Optimise for precision first, and design the product to *degrade
gracefully* when wrong.**

Trust is the whole game. A guard who gets 30 false pings a shift turns Argus off
forever. Levers, in order of impact:

1. **Cascade gating (B1.1)** — most false alarms come from analysing boring
   frames; don't.
2. **Hysteresis + consecutive-N + cooldown** (in `docs/01`): require the concern
   to *persist* across a couple of samples, and never storm.
3. **Confidence tiers, not a binary alarm.** Don't "ALARM." Instead:
   *"review queue" (low), "notify" (medium), "urgent" (high).* Most output goes
   to a passive review queue the operator scans, not an interrupt.
4. **The reason is the trust anchor.** Because a VLM *explains itself*
   ("item concealed in jacket near exit"), the operator can dismiss a bad alert
   in 2 seconds. That's a structural advantage over a black-box "anomaly = 0.87."
5. **Feedback loop.** Every operator dismiss/confirm is a label. Feed it into
   per-site threshold auto-tuning (and eventually fine-tuning). The system gets
   quieter the longer it runs.
6. **Per-site calibration.** A jewellery counter and a warehouse dock have
   different baselines. Thresholds are per-camera, not global.

**[WATCH]** The metric that matters operationally isn't AUC — it's **false
alarms per camera per shift**. Track that as the north-star quality number.

### Q1.4 — Temporal context without exploding cost
Answered by B1.2 (N-frame stacks / event-triggered clips) + B1.1 (only after
Stage 0 fires). You get intent by looking at a *short burst around motion*, not
by watching everything continuously. Optionally keep a rolling **scene memory**
(a short text summary of the last few minutes) and feed it as context to the VLM
so it reasons over continuity cheaply — text is far cheaper than pixels.

### Q1.5 — Hard visual conditions
**[WATCH / HYPOTHESIS]** VLMs degrade on night/IR, heavy occlusion, dense
crowds, glare, extreme angles, and sub-VGA resolution — same as humans, often
worse. Mitigations: (a) restrict v0 claims to "usable lighting, fixed camera"
(already a stated constraint); (b) IR/night is a Phase-2 model-selection problem
(some open VLMs handle IR poorly — test explicitly); (c) crowded scenes are the
hardest — lean on Stage-0 person-tracking to crop to individuals; (d) be honest
in output: a VLM that says "low visibility, cannot assess" is a *feature*, not a
failure. **Never let low-confidence read as high-confidence.**

### Q1.6 — Measuring without a labelled dataset
**[DECISION] Bootstrap evaluation; don't wait for a perfect dataset.**
- Use public shoplifting/anomaly datasets (DCSASS, UCF-Crime-style, retail
  pose-anomaly benchmarks) for a first precision/recall read.
- Stage staged clips ourselves (cheap, controllable, covers our specific cues).
- Once live, **every operator decision is a label** — the deployed system *is*
  the data flywheel. This is why the feedback loop (B1.3) is strategic, not just
  UX polish: it's how we get proprietary training data competitors don't have.

### Q1.7 — Hallucinated reasons
**[DECISION]** Force structured output; log raw text; **calibrate**. Treat the
*score* as the decision signal and the *reason* as explanation — but validate
that reasons correlate with reality on the eval set, and down-weight a model
whose reasons are fluent nonsense. Prefer models that can say "uncertain."
Cross-check high-stakes alerts with a second cheap pass ("do you still agree?").

### Q1.8 — Adversarial adaptation
**[WATCH / BET]** Determined thieves will learn the blind spots (act between
samples, exploit angles). Partial answers: randomise/shorten sampling on
motion so there's no safe gap; keep the model roster and prompts updatable
server-side; treat this as an ongoing arms race, not a solved problem. Honestly:
Argus raises the cost of casual theft a lot; it won't stop a pro who studied it.
That's an acceptable v1 truth — say it plainly to customers.

---

## B2. Model choice & cost — *the make-or-break section*

### Q2.1 — Claude vs Gemini vs GPT vs open-source
**[DECISION] Open-source (Qwen3-VL / InternVL3 class) as the default workhorse;
frontier APIs only as an escalation tier and during prototyping.** Here's the
reasoning, not just the verdict.

Per-image cost spans **~13× across providers** (mid-2026): roughly

| Provider (vision) | ~$/image | Relative |
|---|---|---|
| Qwen-VL (open/hosted) | ~$0.0003 | 1× |
| Gemini (Flash-class) | ~$0.0005 | ~1.7× |
| GPT vision | ~$0.0019 | ~6× |
| Claude vision | ~$0.0040 | ~13× |

Claude is the **best at document/chart reasoning** and GPT is the **safest
generalist**, but for "is this person concealing an item," a well-prompted
8B open VLM is *good enough* and ~13× cheaper than Claude, ~6× cheaper than GPT.
In a workload defined by **volume × always-on**, cost dominates capability past
a low quality bar. So:

- **Prototype** on a hosted frontier VLM (Gemini Flash for cost/latency, or
  Claude for the hardest borderline cases) to move fast and set an accuracy
  ceiling to chase.
- **Production Stage-1** on a **self-hosted open VLM** — the economics below make
  this non-negotiable at scale.
- **Frontier as Stage-2 escalation** only, on the rare borderline high-stakes
  frame, where paying $0.004 once is fine.

### Q2.2 — What it *actually* costs per camera-month (why naive dies)
This is the number every founder in this space must internalise. One camera,
**naive per-frame API calling at k = 5s**:

```
3600 / 5      = 720 calls/hour
720 × 24      = 17,280 calls/day
× 30          ≈ 518,000 VLM calls / camera / month
```

Multiply by per-image price:

| Model | $/image | **$/camera/month (naive, k=5s)** |
|---|---|---|
| Qwen-VL | 0.0003 | **~$155** |
| Gemini Flash | 0.0005 | **~$259** |
| GPT vision | 0.0019 | **~$984** |
| Claude | 0.0040 | **~$2,073** |

**Nobody pays $155–$2,000/month per camera** when cloud VSaaS + analytics sells
for ~$10–50/camera/month. **Naive per-frame frontier calling is dead on
arrival.** This single table is why the architecture *has* to be a cascade, and
why self-hosting matters.

### Q2.3 — Self-hosted open model vs hosted API (and the crossover)
**[DECISION] Self-host at scale; the crossover is very early.**

Self-hosting flips the cost model from **per-call** to **per-GPU-hour amortised
across cameras**:

- One modern GPU running a quantised 8B VLM does ~**2–4 inferences/sec**.
- With the **Stage-0 cascade**, only ~**5–10% of frames** reach the VLM (most
  scenes are empty). Effective VLM load per camera at k=5s drops from 0.2 calls/s
  to ~0.01–0.02 calls/s.
- So one GPU (~$1/hr cloud, less if owned) can serve **~100–200 cameras**.
- Cost/camera-month ≈ `$1/hr × 730 hr ÷ 150 cameras` ≈ **~$5/camera/month**, and
  falling with better gating and owned hardware.

That's a **30–400× improvement** over the naive API table, and it lands *inside*
a sellable price. The API-vs-self-host crossover happens at a **handful of
cameras** — basically as soon as you're past a demo. **[WATCH]** the real costs
then become GPU ops, autoscaling, and utilisation, not per-token price.

### Q2.4 — Where inference runs (edge vs regional vs cloud)
**[BET] Hybrid, edge-first for the cheap stages.**
- **Stage 0 (motion/person) runs at the edge** — on the camera, an NVR, or a
  small box (Jetson-class). It's cheap, and it means we **don't ship 99% of
  video anywhere** (solves B3.3 bandwidth).
- **Stage 1 VLM** runs **regionally** (a GPU box on-prem for big sites, or a
  regional cloud GPU for many small sites) — close enough for latency, central
  enough to amortise GPUs.
- **Stage 2 / frontier** in the cloud, rarely.

This edge-gate + regional-VLM split is the core scaling architecture. It also
gives on-prem/air-gapped customers a story (B4.4).

### Q2.5 — Fine-tune or not?
**[DECISION] Not in v0/v1. Zero-shot + prompt + per-site thresholds first.**
Fine-tuning only once the operator-feedback flywheel (B1.6) has produced enough
proprietary labels that a small fine-tune measurably beats prompting — then it
becomes a *moat* (B5.4), not just an optimisation. Sequence matters: data first,
tuning later.

---

## B3. Scale & architecture

### Q3.1 — One user, multiple cameras
**[DECISION]** This is the *normal* case, not an edge case — a shop has 4–20
cameras; a chain has thousands. What changes:
- **Shared GPU pool, not one-model-per-camera.** Cameras are producers into a
  shared inference queue; the cascade keeps aggregate VLM load low. Adding a
  camera adds Stage-0 load (cheap) and a small slice of Stage-1.
- **Cross-camera context** becomes possible and valuable: the same person moving
  across cameras, a site-wide "alert level," dwell-time patterns. (Explicitly
  *behaviour/track*, still **not identity/face-rec** — B6.)
- **Per-site tuning & one pane of glass:** an operator watches N cameras through
  one review queue, prioritised by score.
- This is exactly the Phase-3 work in `docs/00`; v0 stays single-camera on
  purpose so the loop is proven before the fan-out.

### Q3.2 — 1 → 1,000,000 cameras without linear frontier bills
Answered structurally by **B1.1 cascade + B2.3 self-host + B2.4 edge gating**.
The principle: **cost must scale with *events*, not with *frames* or *cameras*.**
Empty scenes must be nearly free. If cost ever scales linearly with camera-count
× frame-rate × frontier-price, the business is dead — so the whole architecture
exists to break that coupling.

### Q3.3 — Bandwidth & storage
**[DECISION] Don't move raw video by default.** Edge Stage-0 means only
*interesting snippets/frames* (or just *events + evidence thumbnails*) leave the
site. That cuts upload bandwidth by ~1–2 orders of magnitude and shrinks cloud
storage to "evidence for flagged events," with short, configurable retention
(privacy + cost). Customers who want full cloud recording (VSaaS) can opt in and
pay for it — but detection doesn't *require* it.

### Q3.4 — Keeping per-camera cost under the price line
Everything above rolls up to a target: **compute cost/camera-month well under
the sell price.** With cascade + self-host + edge gating we modelled ~$5 and
falling (B2.3) against a ~$10–50 price — a workable gross margin. Guarding that
ratio (utilisation, gating rate, model size) *is* the core engineering KPI.

### Q3.5 — Multi-tenancy & reliability
**[WATCH]** Standard-but-nontrivial: tenant isolation of video/evidence, regional
data residency, GPU autoscaling and bin-packing for utilisation, graceful
degradation (if the VLM tier is saturated, fall back to Stage-0 alerts +
queue, never drop to silent). Reliability of *alerting* is the promise; design
for "degrade loudly," never "fail silent."

---

## B4. Integration with existing setups

### Q4.1 — Plugging into installed cameras
**[DECISION] Standards-first, software-overlay.** Most prospects **already have
cameras**. Meet them where they are:
- **RTSP / ONVIF** are the universal interfaces — support them and you speak to
  the vast majority of IP cameras and NVRs.
- **VMS integrations**: Milestone, Genetec, Avigilon, Meraki, Eagle Eye expose
  SDKs/APIs — integrate as an *analytics layer* on top rather than replacing the
  VMS. Ride the incumbent instead of fighting it.
- **A small on-site connector/appliance** pulls RTSP locally, runs Stage-0, and
  talks to Argus — no rip-and-replace.

### Q4.2 — Software-overlay vs full-stack hardware
**[BET] Lead software-overlay (BYO camera); keep a reference appliance.**
- **Overlay** = faster adoption, no capex for the customer, works on the
  installed base of *billions* of existing cameras. This is the wedge.
- **Full-stack** (Verkada's model — sell the camera + cloud) has better margins
  and lock-in but is a hardware business with long sales cycles and huge capital
  needs; it's how the incumbent got to #1, and competing there head-on is brutal
  for a newcomer.
- **Reference edge box** (a validated Jetson-class connector) de-risks
  deployment for non-technical customers without making us a hardware company.

### Q4.3 — How alerts reach the human
**[DECISION] Meet the operator's existing workflow.** Push to: a mobile app
(small sites), SMS/WhatsApp/webhook, and — critically — **back into the
customer's existing VMS/SOC** as events, so we're additive to their console, not
a second screen they'll ignore. Alert = score + reason + evidence thumbnail +
deep link to the clip.

### Q4.4 — On-prem / air-gapped
**[DECISION]** The **self-hosted open-VLM** stack (B2.3) is a first-class
selling point here: sensitive customers (gov, critical infra, some retail) can
run the *entire* pipeline on-prem with **no video leaving the building** — a
story the frontier-API-only competitors structurally cannot tell. This turns our
cost strategy (open models) into a *product differentiator*.

---

## B5. Business, market & competition

### Q5.1 — Market size & the winnable slice
**[grounded]** The AI-in-video-surveillance market is roughly **$6–8B in 2026**,
growing **~14–23% CAGR** to **~$11–15B+ by 2030–32**; the broader VSaaS market
is ~**$7.6B (2026) → ~$15.6B (2031)** at ~15.5% CAGR (estimates vary by
definition). It's large, growing double digits, and fragmented.
**Winnable slice:** not "all surveillance." Start with a **specific, high-pain
vertical + specific event type** — e.g. **shrinkage/shoplifting for
small-and-mid retail**, where the ROI is a hard dollar number (retail shrink is
a well-known multi-hundred-billion global problem) and the buyer is
underserved by enterprise-priced incumbents.

### Q5.2 — Existing players & not getting crushed
**[grounded / WATCH]** The landscape:
- **Full-stack VSaaS incumbents:** Verkada (#1), Cisco/Meraki, Motorola
  (Avigilon/Pelco), Hanwha, Axis — sell cameras + cloud + analytics; strong, but
  **expensive, hardware-locked, enterprise sales motion.**
- **VMS platforms:** Genetec, Milestone, Eagle Eye — own the software layer;
  potential **partners or channels**, not just competitors.
- **AI-analytics specialists:** Ambient.ai (enterprise behaviour detection),
  Deep Sentinel (consumer/SMB live-guard), and a wave of VLM-native startups.

**How not to get crushed:** don't fight Verkada on hardware. Win on
(a) **software-overlay on the installed base** (no capex), (b) **VLM-native
explainability** (every alert has a human reason — incumbents' analytics are
often black-box), (c) **open-model cost + on-prem privacy** they can't match on
their cloud economics, and (d) a **focused vertical** where we're 10× better at
one thing, not 10% better at everything.

### Q5.3 — Revenue model
**[BET] Per-camera-per-month SaaS as the base, tiered by capability.**
- **Base:** ~$10–40 / camera / month for detection + alerts + review queue
  (undercuts full-stack incumbents; overlay = no hardware cost to customer).
- **Tiers:** more event types, longer retention, VMS integration, on-prem, SLAs.
- **Usage add-ons:** cloud clip storage (VSaaS), frontier-model "high-assurance"
  escalation, human-verified alerts (a monitored-guard upsell like Deep
  Sentinel's).
- **Avoid pure per-alert pricing** as the base — it perversely punishes the
  customer for the system working and makes bills unpredictable.
- **Land-and-expand:** start on a few cameras, grow across the site/chain.

### Q5.4 — The moat (VLMs are a commodity — so what's defensible?)
**[BET] The moat is *not* the model. It's:**
1. **The proprietary feedback dataset** (B1.6) — every deployed camera generates
   labelled operator decisions we own; that data trains models competitors can't
   replicate. *Data flywheel.*
2. **Per-site calibration + low false-alarm tuning** — the operational know-how
   to make it *quiet*, which is where most VLM demos fail.
3. **Integration surface** — deep, boring plumbing into VMS/cameras/workflows
   that's painful to rebuild.
4. **Cost architecture** — the cascade + self-host stack that makes the unit
   economics work is itself hard-won engineering.
5. **Trust/brand in a domain where being wrong is expensive.**
Anyone can prompt a VLM; few can make it cheap, quiet, integrated, and trusted
at a million cameras.

### Q5.5 — Go-to-market / wedge
**[BET]** Wedge = **SMB retail shrink**, sold as **"software that turns the
cameras you already own into a theft-alerting system for $X/camera, live in an
afternoon."** No hardware, self-serve-ish onboarding, ROI framed against a known
shrink number. Expand from single shops → local chains → verticals adjacent to
retail (convenience, pharmacy, warehousing).

### Q5.6 — Unit economics
**[HYPOTHESIS]** With compute ~$5/camera-month (B2.3) against a ~$10–40 price,
**gross margin is workable and improves with scale** (better GPU utilisation,
better gating, owned hardware, eventual fine-tuned small models). The economic
thesis lives or dies on the **gating rate and GPU utilisation**, which is why
they're the core engineering KPIs, not vanity accuracy metrics.

---

## B6. Legal, ethical & trust at scale

- **Q6.1 Liability [DECISION]:** Argus is **decision-support, not an accuser.**
  Human-in-the-loop is both product and legal posture — we surface a scored,
  explained observation; a *person* acts. Contractually position as an alerting
  aid, not proof of guilt. Never auto-detain/auto-act.
- **Q6.2 Bias [WATCH, hard requirement]:** monitor per-group flag rates in
  aggregate, red-team the prompts, and treat systematic over-flagging as a
  release blocker. A biased surveillance product is both an ethical failure and
  an existential PR/legal risk.
- **Q6.3 Privacy law [DECISION]:** design for **GDPR / BIPA / state biometric
  laws / India DPDP** from day one — no face recognition (dodges most biometric
  regimes), data minimisation, short default retention, per-region residency,
  and an **on-prem mode** for customers who can't send video out. "Behaviour,
  not identity" is a compliance strategy as much as an ethical one.
- **Q6.4 Human-in-the-loop:** the review-queue + confidence-tier UX (B1.3) *is*
  the safety mechanism. Keep it central even when it would be cheaper to
  auto-alert.

---

## Decisions summary (the load-bearing calls)

1. **Architecture is a cascade** (cheap edge filter → cheap VLM → rare expensive
   escalation), so cost scales with *events*, not frames. *(B1.1, B3.2)*
2. **Open-source VLM self-hosted is the production workhorse;** frontier APIs are
   prototyping + rare escalation only — naive per-frame frontier calling is
   economically dead (~$155–$2,000/camera-month). *(B2.1–B2.3)*
3. **Unit of analysis slides from single-frame → N-frame stack → short clip;**
   start single-frame, move to event-triggered stacks for temporal intent; never
   dense video. *(B1.2)*
4. **Precision-first, degrade-gracefully product:** confidence tiers + review
   queue + explainable reasons + operator-feedback flywheel; north-star metric is
   *false alarms per camera per shift.* *(B1.3, B1.6)*
5. **Edge-gate + regional-VLM** so raw video mostly never leaves the site
   (bandwidth, cost, privacy, on-prem story). *(B2.4, B3.3, B4.4)*
6. **Software-overlay on the installed base** (RTSP/ONVIF/VMS) is the GTM wedge;
   reference edge appliance, not a hardware company. *(B4.1, B4.2, B5.5)*
7. **Moat = data flywheel + quiet-tuning know-how + integrations + cost
   architecture + trust,** not the model itself. *(B5.4)*
8. **Behaviour-not-identity + human-in-the-loop** are simultaneously the ethics,
   the compliance strategy, and the liability posture. *(B6)*

---

## Open questions still to resolve
- Best default `k` and unit-of-analysis per vertical (measure — Q1.2, `docs/00` Q1/Q2).
- Which specific open VLM wins the cost/accuracy bake-off (Q2.1, `docs/00` Q3).
- Real gating rate on live footage → the number the whole cost model rides on (B3.4).
- Exact wedge vertical and pricing validated against a paying design partner (B5.5/B5.6).
- IR/night viability per candidate model (B1.5).

---

## References (2026)

**Market**
- VSaaS market size — Mordor Intelligence:
  <https://www.mordorintelligence.com/industry-reports/video-surveillance-as-a-service-vsaas-market>
- AI in video surveillance market — Mordor:
  <https://www.mordorintelligence.com/industry-reports/ai-in-video-surveillance-market>
- AI in video surveillance — MarketsandMarkets:
  <https://www.marketsandmarkets.com/Market-Reports/ai-in-video-surveillance-market-84216922.html>
- Verkada #1 VSaaS (Omdia):
  <https://www.verkada.com/blog/leading-cloud-video-security/>
- Build vs buy / cost, Forasoft:
  <https://www.forasoft.com/blog/article/custom-video-surveillance-solutions>
- Top AI surveillance vendors 2026, ActionStreamer:
  <https://actionstreamer.com/blog/top-6-ai-surveillance-vendors-for-enterprise-in-2026>

**Model cost**
- Vision API pricing comparison (per-image, tokenization), TokenMix:
  <https://tokenmix.ai/blog/vision-api-comparison>
- AI API pricing comparison 2026, DevTk:
  <https://devtk.ai/en/blog/ai-api-pricing-comparison-2026/>

**Detection research** (see also `docs/00` references)
- *Are Multimodal LLMs Ready for Surveillance?* — <https://arxiv.org/pdf/2603.04727>
- *Zero-Shot Retail Theft Detection via Orchestrated Vision Models* — <https://arxiv.org/pdf/2604.14846>

*Figures are order-of-magnitude and time-sensitive; re-check before quoting in
any external or fundraising material.*
