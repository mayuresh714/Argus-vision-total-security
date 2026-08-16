// Orchestrates the three-tier scan-escalation pipeline for each active
// camera:
//
//   sample frame ──► Tier 1 (fast local scan, every frame)
//                        │ score >= TIER1_SUSPICION_THRESHOLD ("doubt")
//                        ▼
//                    Tier 2 (local VLM)
//                        │ confidence < TIER2_CONFIDENCE_ESCALATE_BELOW ("more doubt")
//                        ▼
//                    Tier 3 (sophisticated model)
//                        │
//                        ▼
//              final score >= camera.alertThreshold ──► create Alert + notify
//
// Each tier only runs when the previous one is unsure, keeping the expensive
// models off the hot path for the (vast majority of) uneventful frames.
import { v4 as uuid } from 'uuid';
import { getCamera, listCameras, createAlert, updateCamera } from '../models/store.js';
import { emit } from '../ws/io.js';
import { runTier1 } from './models/tier1Heuristic.js';
import { runTier2 } from './models/tier2LocalVlm.js';
import { runTier3 } from './models/tier3Sophisticated.js';

const TIER1_SUSPICION_THRESHOLD = Number(process.env.TIER1_SUSPICION_THRESHOLD ?? 0.35);
const TIER2_CONFIDENCE_ESCALATE_BELOW = Number(process.env.TIER2_CONFIDENCE_ESCALATE_BELOW ?? 0.6);
const ALERT_SCORE_THRESHOLD = Number(process.env.ALERT_SCORE_THRESHOLD ?? 0.55);

const runningLoops = new Map(); // cameraId -> interval handle

function sampleFrame(camera) {
  // Simulated frame — in a real deployment this grabs the freshest decoded
  // frame from the RTSP stream and base64-encodes a JPEG for the VLM calls.
  return {
    id: uuid(),
    cameraId: camera.id,
    ts: new Date().toISOString(),
    imageBase64: null,
    // A deterministic-looking "evidence" placeholder image path.
    path: `/evidence/${camera.id}/${Date.now()}.jpg`,
  };
}

export async function analyzeFrame(camera, frame) {
  const trace = [];

  const tier1 = await runTier1(frame);
  trace.push(tier1);
  emit('scan:tier', { cameraId: camera.id, frameId: frame.id, ...tier1 });

  let final = tier1;

  if (tier1.score >= TIER1_SUSPICION_THRESHOLD) {
    const tier2 = await runTier2(frame, tier1);
    trace.push(tier2);
    emit('scan:tier', { cameraId: camera.id, frameId: frame.id, ...tier2 });
    final = tier2;

    if ((tier2.confidence ?? 1) < TIER2_CONFIDENCE_ESCALATE_BELOW) {
      const tier3 = await runTier3(frame, tier1, tier2);
      trace.push(tier3);
      emit('scan:tier', { cameraId: camera.id, frameId: frame.id, ...tier3 });
      final = tier3;
    }
  }

  const result = {
    frameId: frame.id,
    cameraId: camera.id,
    ts: frame.ts,
    finalTier: final.tier,
    score: final.score,
    confidence: final.confidence ?? null,
    reason: final.reason,
    tags: final.tags || [],
    trace,
  };

  emit('frame:analyzed', result);

  const threshold = camera.alertThreshold ?? ALERT_SCORE_THRESHOLD;
  if (final.score >= threshold) {
    const alert = createAlert({
      cameraId: camera.id,
      cameraName: camera.name,
      frameId: frame.id,
      framePath: frame.path,
      score: final.score,
      confidence: final.confidence ?? null,
      reason: final.reason,
      tags: final.tags || [],
      finalTier: final.tier,
      trace,
    });
    emit('alert:new', { alert });
    return { result, alert };
  }

  return { result, alert: null };
}

export function startCameraLoop(cameraId) {
  stopCameraLoop(cameraId);
  const camera = getCamera(cameraId);
  if (!camera) return;
  const intervalMs = Math.max(1, camera.sampleIntervalSeconds || 5) * 1000;

  const handle = setInterval(async () => {
    const cam = getCamera(cameraId);
    if (!cam || cam.status !== 'online') return;
    const frame = sampleFrame(cam);
    updateCamera(cameraId, { lastFrameAt: frame.ts });
    emit('frame:sampled', { cameraId, frameId: frame.id, ts: frame.ts });
    try {
      await analyzeFrame(cam, frame);
    } catch (err) {
      emit('camera:error', { cameraId, error: String(err?.message || err) });
    }
  }, intervalMs);

  runningLoops.set(cameraId, handle);
}

export function stopCameraLoop(cameraId) {
  const handle = runningLoops.get(cameraId);
  if (handle) {
    clearInterval(handle);
    runningLoops.delete(cameraId);
  }
}

export function startAllCameraLoops() {
  for (const camera of listCameras()) {
    if (camera.status === 'online') startCameraLoop(camera.id);
  }
}
