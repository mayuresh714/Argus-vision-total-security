import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';

export default function Settings() {
  const { user } = useAuth();
  const [cameras, setCameras] = useState([]);
  const [savingId, setSavingId] = useState(null);

  async function load() {
    const { cameras } = await api.listCameras();
    setCameras(cameras);
  }

  useEffect(() => {
    load();
  }, []);

  async function save(camera, patch) {
    setSavingId(camera.id);
    try {
      await api.updateCamera(camera.id, patch);
      await load();
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="page">
      <h1>Settings</h1>

      <section className="section">
        <h2>Account</h2>
        <div className="row-card">
          <div className="row-card-main">
            <strong>{user?.name}</strong>
            <span className="muted">{user?.email} · {user?.role}</span>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Per-camera tuning</h2>
        <p className="muted">Sampling cadence (k) and the alert score threshold, per the three-tier escalation pipeline.</p>
        <div className="list">
          {cameras.map((c) => (
            <div key={c.id} className="tuning-card">
              <strong>{c.name}</strong>
              <label>Sample interval: {c.sampleIntervalSeconds}s</label>
              <input
                type="range" min="2" max="30" value={c.sampleIntervalSeconds}
                onChange={(e) => save(c, { sampleIntervalSeconds: Number(e.target.value) })}
              />
              <label>Alert threshold: {Math.round(c.alertThreshold * 100)}%</label>
              <input
                type="range" min="0" max="1" step="0.05" value={c.alertThreshold}
                onChange={(e) => save(c, { alertThreshold: Number(e.target.value) })}
              />
              {savingId === c.id && <span className="muted small">Saving…</span>}
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <h2>Model pipeline</h2>
        <p className="muted">
          Tier 1 (fast local scan) runs on every frame. Tier 2 (local VLM) only runs when Tier 1 is
          unsure. Tier 3 (sophisticated model) only runs when Tier 2 is still unsure. Configure
          endpoints via the backend's <code>.env</code> (<code>TIER2_ENDPOINT</code>, <code>TIER3_ENDPOINT</code>).
        </p>
      </section>
    </div>
  );
}
