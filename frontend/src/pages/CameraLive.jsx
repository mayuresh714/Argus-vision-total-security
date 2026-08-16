import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { useSocket } from '../context/SocketContext.jsx';
import AlertCard from '../components/AlertCard.jsx';
import ScoreBadge from '../components/ScoreBadge.jsx';

const TIER_LABEL = {
  1: 'Tier 1 · Fast local scan',
  2: 'Tier 2 · Local VLM',
  3: 'Tier 3 · Sophisticated model',
};

export default function CameraLive() {
  const { id } = useParams();
  const [camera, setCamera] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const { liveTiers, lastAlert } = useSocket();

  async function load() {
    const [{ camera }, { alerts }] = await Promise.all([api.getCamera(id), api.listAlerts({ cameraId: id, limit: 10 })]);
    setCamera(camera);
    setAlerts(alerts);
  }

  useEffect(() => {
    load();
  }, [id]);

  useEffect(() => {
    if (lastAlert?.cameraId === id) load();
  }, [lastAlert]);

  const feed = liveTiers.filter((t) => t.cameraId === id).slice(0, 12);

  if (!camera) return <div className="page">Loading…</div>;

  return (
    <div className="page">
      <Link to="/cameras" className="back-link">← Cameras</Link>
      <div className="section-head">
        <h1>{camera.name}</h1>
        <span className={`pill pill-${camera.status === 'online' ? 'new' : 'dismissed'}`}>{camera.status}</span>
      </div>
      <p className="muted">{camera.location} · sampling every {camera.sampleIntervalSeconds}s · alert ≥ {Math.round(camera.alertThreshold * 100)}%</p>

      <div className="live-preview">
        <div className="live-preview-frame">📹 Live feed preview (simulated)</div>
      </div>

      <section className="section">
        <h2>Three-tier scan pipeline — live</h2>
        <p className="muted">Every sampled frame runs Tier 1. It only escalates to Tier 2 (local VLM) or Tier 3 (sophisticated model) when the previous tier is unsure.</p>
        <div className="tier-feed">
          {feed.length === 0 && <p className="empty-state">Waiting for the next sampled frame…</p>}
          {feed.map((t, i) => (
            <div key={`${t.frameId}-${t.tier}-${i}`} className={`tier-row tier-${t.tier}`}>
              <div className="tier-row-top">
                <span className="tier-name">{TIER_LABEL[t.tier]}</span>
                <ScoreBadge score={t.score} />
              </div>
              <p className="tier-reason">{t.reason}</p>
              <span className="muted small">{t.model} · {t.latencyMs}ms</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <h2>Recent alerts on this camera</h2>
        <div className="alert-list">
          {alerts.length === 0 && <p className="empty-state">No alerts yet.</p>}
          {alerts.map((a) => (
            <AlertCard key={a.id} alert={a} />
          ))}
        </div>
      </section>
    </div>
  );
}
