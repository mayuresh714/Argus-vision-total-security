import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import {
  listCameras,
  getCamera,
  createCamera,
  updateCamera,
  deleteCamera,
} from '../models/store.js';
import { startCameraLoop, stopCameraLoop } from '../services/scanPipeline.js';

const router = Router();
router.use(requireAuth);

router.get('/', (req, res) => {
  res.json({ cameras: listCameras() });
});

router.get('/:id', (req, res) => {
  const camera = getCamera(req.params.id);
  if (!camera) return res.status(404).json({ error: 'Camera not found' });
  res.json({ camera });
});

router.post('/', (req, res) => {
  const { name, location, rtspUrl, sampleIntervalSeconds, alertThreshold } = req.body || {};
  if (!name) return res.status(400).json({ error: 'name required' });
  const camera = createCamera({
    name,
    location: location || '',
    rtspUrl: rtspUrl || '',
    sampleIntervalSeconds: sampleIntervalSeconds || 5,
    alertThreshold: alertThreshold ?? 0.55,
  });
  startCameraLoop(camera.id);
  res.status(201).json({ camera });
});

router.patch('/:id', (req, res) => {
  const camera = updateCamera(req.params.id, req.body || {});
  if (!camera) return res.status(404).json({ error: 'Camera not found' });
  res.json({ camera });
});

router.delete('/:id', (req, res) => {
  stopCameraLoop(req.params.id);
  const ok = deleteCamera(req.params.id);
  if (!ok) return res.status(404).json({ error: 'Camera not found' });
  res.status(204).end();
});

router.post('/:id/toggle', (req, res) => {
  const camera = getCamera(req.params.id);
  if (!camera) return res.status(404).json({ error: 'Camera not found' });
  if (camera.status === 'online') {
    camera.status = 'paused';
    stopCameraLoop(camera.id);
  } else {
    camera.status = 'online';
    startCameraLoop(camera.id);
  }
  res.json({ camera });
});

export default router;
