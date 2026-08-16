// Tier 2 — local VLM (e.g. Qwen3-VL / InternVL3 / Gemma-multimodal running
// on-device / on-prem). Only invoked when Tier 1 flags "worth a closer look".
// Reasons in plain language about the frame and returns a calibrated
// confidence. If Tier 2 is still unsure, the pipeline escalates to Tier 3.
//
// Real integration: POST { imageBase64, prompt } to TIER2_ENDPOINT and expect
// { score, reason, tags, confidence }. Falls back to a mock reasoner so the
// full app works end-to-end without a GPU / local model server.

const ENDPOINT = process.env.TIER2_ENDPOINT;

const PROMPT = `You are a security-monitoring assistant reviewing a single still frame from a
CCTV camera. Rate how suspicious the behaviour in this frame looks (0-1),
explain why in one sentence, and list short tags. Do NOT identify or describe
individuals' faces or personal identity — describe behaviour only.`;

function mockReason(tier1) {
  const base = tier1.score;
  const jitter = (Math.random() - 0.3) * 0.25;
  const score = clamp(base + jitter);
  const confidence = clamp(0.4 + Math.random() * 0.5);
  const reasons = {
    no_activity: 'Frame shows an empty area with no notable behaviour.',
    routine_activity: 'A person is walking through the area in a manner consistent with normal customer/staff behaviour.',
    elevated_motion: 'A person is lingering near shelving and glancing around repeatedly, which can be consistent with either browsing or concealment behaviour.',
    high_motion: 'A person appears to be concealing an item under clothing before moving quickly toward the exit.',
  };
  return {
    tier: 2,
    model: 'local-vlm (mock: qwen3-vl-class)',
    score,
    confidence,
    reason: reasons[tier1.label] || 'Ambiguous behaviour visible in frame; recommend human review.',
    tags: tier1.tags,
  };
}

function clamp(n) {
  return Math.max(0, Math.min(1, Math.round(n * 100) / 100));
}

export async function runTier2(frame, tier1) {
  const start = Date.now();
  if (ENDPOINT) {
    try {
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageBase64: frame.imageBase64, prompt: PROMPT }),
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) throw new Error(`tier2 endpoint ${res.status}`);
      const data = await res.json();
      return { tier: 2, model: 'local-vlm', latencyMs: Date.now() - start, ...data };
    } catch (err) {
      // Fall through to mock so the pipeline degrades gracefully.
    }
  }
  await new Promise((r) => setTimeout(r, 300 + Math.random() * 500));
  return { ...mockReason(tier1), latencyMs: Date.now() - start };
}
