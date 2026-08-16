import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import { listAlerts, getAlert, updateAlert } from '../models/store.js';

const router = Router();
router.use(requireAuth);

router.get('/', (req, res) => {
  const { cameraId, status, limit } = req.query;
  const alerts = listAlerts({ cameraId, status, limit: limit ? Number(limit) : undefined });
  res.json({ alerts });
});

router.get('/:id', (req, res) => {
  const alert = getAlert(req.params.id);
  if (!alert) return res.status(404).json({ error: 'Alert not found' });
  res.json({ alert });
});

router.patch('/:id', (req, res) => {
  const { status } = req.body || {};
  if (!['new', 'acknowledged', 'dismissed'].includes(status)) {
    return res.status(400).json({ error: 'status must be new|acknowledged|dismissed' });
  }
  const alert = updateAlert(req.params.id, { status, reviewedBy: req.user.id, reviewedAt: new Date().toISOString() });
  if (!alert) return res.status(404).json({ error: 'Alert not found' });
  res.json({ alert });
});

export default router;
