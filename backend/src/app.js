import express from 'express';
import cors from 'cors';
import authRoutes from './routes/auth.js';
import cameraRoutes from './routes/cameras.js';
import alertRoutes from './routes/alerts.js';

export function createApp() {
  const app = express();

  app.use(cors({ origin: process.env.CORS_ORIGIN || '*' }));
  app.use(express.json({ limit: '10mb' }));

  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', service: 'argus-backend', ts: new Date().toISOString() });
  });

  app.use('/api/auth', authRoutes);
  app.use('/api/cameras', cameraRoutes);
  app.use('/api/alerts', alertRoutes);

  app.use((req, res) => {
    res.status(404).json({ error: 'Not found' });
  });

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
