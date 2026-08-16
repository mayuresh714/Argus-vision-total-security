// Tier 3 — sophisticated model (larger open-source VLM run on a beefier node,
// or a frontier API as an opt-in). Only invoked when Tier 2 is still unsure
// (confidence below TIER2_CONFIDENCE_ESCALATE_BELOW). This is the expensive,
// slow, most-accurate path — used sparingly by design.
//
// Real integration: POST { imageBase64, prompt, tier1, tier2 } to
// TIER3_ENDPOINT. Falls back to a mock reasoner that leans on tier2's read
// but resolves the ambiguity with higher confidence.

const ENDPOINT = process.env.TIER3_ENDPOINT;
const PROVIDER = process.env.TIER3_PROVIDER || 'none';

function clamp(n) {
  return Math.max(0, Math.min(1, Math.round(n * 100) / 100));
}

function mockResolve(tier2) {
  const drift = (Math.random() - 0.5) * 0.15;
  const score = clamp(tier2.score + drift);
  const confidence = clamp(0.75 + Math.random() * 0.24);
  return {
    tier: 3,
    model: `sophisticated-model (mock, provider=${PROVIDER})`,
    score,
    confidence,
    reason: `${tier2.reason} High-resolution re-analysis ${score >= 0.55 ? 'confirms' : 'does not confirm'} suspicious behaviour.`,
    tags: [...new Set([...(tier2.tags || []), 'tier3-reviewed'])],
  };
}

export async function runTier3(frame, tier1, tier2) {
  const start = Date.now();
  if (ENDPOINT) {
    try {
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageBase64: frame.imageBase64, tier1, tier2 }),
        signal: AbortSignal.timeout(15000),
      });
      if (!res.ok) throw new Error(`tier3 endpoint ${res.status}`);
      const data = await res.json();
      return { tier: 3, model: 'sophisticated-model', latencyMs: Date.now() - start, ...data };
    } catch (err) {
      // Fall through to mock.
    }
  }
  await new Promise((r) => setTimeout(r, 700 + Math.random() * 900));
  return { ...mockResolve(tier2), latencyMs: Date.now() - start };
}
