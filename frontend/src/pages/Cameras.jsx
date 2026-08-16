import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';

const empty = { name: '', location: '', rtspUrl: '', sampleIntervalSeconds: 5, alertThreshold: 0.55 };

export default function Cameras() {
  const [cameras, setCameras] = useState([]);
  const [form, setForm] = useState(empty);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    const { cameras } = await api.listCameras();
    setCameras(cameras);
  }

  useEffect(() => {
    load();
  }, []);

  async function onCreate(e) {
    e.preventDefault();
    setError('');
    try {
      await api.createCamera(form);
      setForm(empty);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function onToggle(id) {
    await api.toggleCamera(id);
    load();
  }

  async function onDelete(id) {
    if (!confirm('Remove this camera?')) return;
    await api.deleteCamera(id);
    load();
  }

  return (
    <div className="page">
      <div className="section-head">
        <h1>Cameras</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? 'Cancel' : '+ Add camera'}
        </button>
      </div>

      {showForm && (
        <form className="card-form" onSubmit={onCreate}>
          <label>Name</label>
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <label>Location</label>
          <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          <label>RTSP URL</label>
          <input value={form.rtspUrl} onChange={(e) => setForm({ ...form, rtspUrl: e.target.value })} placeholder="rtsp://…" />
          <label>Sample interval (seconds)</label>
          <input type="number" min="1" value={form.sampleIntervalSeconds} onChange={(e) => setForm({ ...form, sampleIntervalSeconds: Number(e.target.value) })} />
          <label>Alert threshold (0–1)</label>
          <input type="number" step="0.05" min="0" max="1" value={form.alertThreshold} onChange={(e) => setForm({ ...form, alertThreshold: Number(e.target.value) })} />
          {error && <p className="form-error">{error}</p>}
          <button className="btn-primary" type="submit">Create camera</button>
        </form>
      )}

      <div className="list">
        {cameras.map((c) => (
          <div key={c.id} className="row-card">
            <Link to={`/cameras/${c.id}`} className="row-card-main">
              <strong>{c.name}</strong>
              <span className="muted">{c.location || '—'}</span>
            </Link>
            <div className="row-card-actions">
              <span className={`pill pill-${c.status === 'online' ? 'new' : 'dismissed'}`}>{c.status}</span>
              <button className="btn-ghost" onClick={() => onToggle(c.id)}>{c.status === 'online' ? 'Pause' : 'Resume'}</button>
              <button className="btn-ghost btn-danger" onClick={() => onDelete(c.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
