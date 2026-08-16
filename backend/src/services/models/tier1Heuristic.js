// Tier 1 — fast local scan. Cheap motion/pixel-delta style heuristic that runs
// on *every* sampled frame with sub-50ms latency. Its only job is to decide
// "is there anything worth a closer (expensive) look?" It never raises an
// alert on its own — only escalates.
//
// Swap this out for a real motion-detector / lightweight object-detector
// (e.g. background-subtraction + a tiny YOLO-nano) without touching the
// pipeline — it just needs to return { score, label, reason }.

const SCENARIOS = [
  { weight: 0.55, label: 'no_activity', score: () => rand(0.0, 0.12), reason: 'No significant motion detected.' },
  { weight: 0.2, label: 'routine_activity', score: () => rand(0.1, 0.3), reason: 'Ordinary foot traffic / staff movement detected.' },
  { weight: 0.15, label: 'elevated_motion', score: () => rand(0.3, 0.6), reason: 'Unusual motion pattern near a high-value area — escalating for deeper analysis.' },
  { weight: 0.1, label: 'high_motion', score: () => rand(0.55, 0.9), reason: 'Rapid or erratic motion detected — escalating for deeper analysis.' },
];

function rand(min, max) {
  return Math.round((min + Math.random() * (max - min)) * 100) / 100;
}

function pickScenario() {
  const r = Math.random();
  let acc = 0;
  for (const s of SCENARIOS) {
    acc += s.weight;
    if (r <= acc) return s;
  }
  return SCENARIOS[0];
}

export async function runTier1(frame) {
  const start = Date.now();
  const scenario = pickScenario();
  const score = scenario.score();
  await new Promise((r) => setTimeout(r, 15 + Math.random() * 20));
  return {
    tier: 1,
    model: 'tier1-fast-heuristic',
    score,
    label: scenario.label,
    reason: scenario.reason,
    tags: [scenario.label],
    latencyMs: Date.now() - start,
  };
}
