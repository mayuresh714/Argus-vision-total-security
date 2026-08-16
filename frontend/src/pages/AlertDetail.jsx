import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client.js';
import ScoreBadge from '../components/ScoreBadge.jsx';

const TIER_LABEL = { 1: 'Tier 1 · Fast local scan', 2: 'Tier 2 · Local VLM', 3: 'Tier 3 · Sophisticated model' };

export default function AlertDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [alert, setAlert] = useState(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const { alert } = await api.getAlert(id);
    setAlert(alert);
  }

  useEffect(() => {
    load();
  }, [id]);

  async function setStatus(status) {
    setBusy(true);
    try {
      const { alert } = await api.updateAlertStatus(id, status);
      setAlert(alert);
    } finally {
      setBusy(false);
    }
  }

  if (!alert) return <div className="page">Loading…</div>;

  return (
    <div className="page">
      <Link to="/alerts" className="back-link">← Alerts</Link>
      <div className="section-head">
        <h1>{alert.cameraName}</h1>
        <ScoreBadge score={alert.score} />
      </div>
      <p className="muted">{new Date(alert.createdAt).toLocaleString()} · resolved at {TIER_LABEL[alert.finalTier]}</p>

      <div className="evidence-frame">🎞️ Evidence frame</div>

      <section className="section">
        <h2>Why Argus flagged this</h2>
        <p className="reason-block">{alert.reason}</p>
        <div className="tag-row">
          {alert.tags?.map((t) => <span key={t} className="chip">{t}</span>)}
        </div>
      </section>

      <section className="section">
        <h2>Escalation trace</h2>
        <div className="tier-feed">
          {alert.trace?.map((t, i) => (
            <div key={i} className={`tier-row tier-${t.tier}`}>
              <div className="tier-row-top">
                <span className="tier-name">{TIER_LABEL[t.tier]}</span>
                <ScoreBadge score={t.score} />
              </div>
              <p className="tier-reason">{t.reason}</p>
              <span className="muted small">{t.model} · {t.latencyMs}ms{t.confidence != null ? ` · confidence ${Math.round(t.confidence * 100)}%` : ''}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section action-bar">
        <button className="btn-primary" disabled={busy || alert.status === 'acknowledged'} onClick={() => setStatus('acknowledged')}>
          Acknowledge
        </button>
        <button className="btn-ghost" disabled={busy || alert.status === 'dismissed'} onClick={() => setStatus('dismissed')}>
          Dismiss (false alarm)
        </button>
        <button className="btn-ghost" onClick={() => navigate(`/cameras/${alert.cameraId}`)}>View camera</button>
      </section>
    </div>
  );
}
