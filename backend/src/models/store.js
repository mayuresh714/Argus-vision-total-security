// In-memory data store. Swap for a real DB (Postgres/SQLite) behind the same
// functions without touching routes/services.
import { v4 as uuid } from 'uuid';
import bcrypt from 'bcryptjs';

export const db = {
  users: [],
  cameras: [],
  alerts: [],
};

function seed() {
  const passwordHash = bcrypt.hashSync('argus123', 8);
  db.users.push({
    id: uuid(),
    name: 'Demo Operator',
    email: 'operator@argus.demo',
    passwordHash,
    role: 'admin',
    createdAt: new Date().toISOString(),
  });

  const cams = [
    { name: 'Front Entrance', location: 'Store Front', rtspUrl: 'rtsp://demo/front' },
    { name: 'Cash Counter', location: 'Register Area', rtspUrl: 'rtsp://demo/counter' },
    { name: 'Warehouse Aisle 3', location: 'Backroom', rtspUrl: 'rtsp://demo/aisle3' },
    { name: 'Loading Dock', location: 'Rear Exit', rtspUrl: 'rtsp://demo/dock' },
  ];
  for (const c of cams) {
    db.cameras.push({
      id: uuid(),
      ...c,
      status: 'online',
      sampleIntervalSeconds: 5,
      alertThreshold: 0.55,
      createdAt: new Date().toISOString(),
      lastFrameAt: null,
    });
  }
}

seed();

export function findUserByEmail(email) {
  return db.users.find((u) => u.email.toLowerCase() === email.toLowerCase());
}

export function findUserById(id) {
  return db.users.find((u) => u.id === id);
}

export function createUser({ name, email, passwordHash, role = 'viewer' }) {
  const user = { id: uuid(), name, email, passwordHash, role, createdAt: new Date().toISOString() };
  db.users.push(user);
  return user;
}

export function listCameras() {
  return db.cameras;
}

export function getCamera(id) {
  return db.cameras.find((c) => c.id === id);
}

export function createCamera(data) {
  const camera = {
    id: uuid(),
    status: 'online',
    sampleIntervalSeconds: 5,
    alertThreshold: 0.55,
    createdAt: new Date().toISOString(),
    lastFrameAt: null,
    ...data,
  };
  db.cameras.push(camera);
  return camera;
}

export function updateCamera(id, patch) {
  const camera = getCamera(id);
  if (!camera) return null;
  Object.assign(camera, patch);
  return camera;
}

export function deleteCamera(id) {
  const idx = db.cameras.findIndex((c) => c.id === id);
  if (idx === -1) return false;
  db.cameras.splice(idx, 1);
  db.alerts = db.alerts.filter((a) => a.cameraId !== id);
  return true;
}

export function listAlerts({ cameraId, status, limit = 100 } = {}) {
  let items = db.alerts;
  if (cameraId) items = items.filter((a) => a.cameraId === cameraId);
  if (status) items = items.filter((a) => a.status === status);
  return items
    .slice()
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .slice(0, limit);
}

export function getAlert(id) {
  return db.alerts.find((a) => a.id === id);
}

export function createAlert(data) {
  const alert = {
    id: uuid(),
    status: 'new', // new | acknowledged | dismissed
    createdAt: new Date().toISOString(),
    ...data,
  };
  db.alerts.unshift(alert);
  return alert;
}

export function updateAlert(id, patch) {
  const alert = getAlert(id);
  if (!alert) return null;
  Object.assign(alert, patch);
  return alert;
}
