import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { useSocket } from '../context/SocketContext.jsx';
import AlertCard from '../components/AlertCard.jsx';

export default function Dashboard() {
  const [cameras, setCameras] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const { lastAlert } = useSocket();

  async function load() {
    const [c, a] = await Promise.all([api.listCameras(), api.listAlerts({ limit: 6 })]);
    setCameras(c.cameras);
    setAlerts(a.alerts);
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (lastAlert) load();
  }, [lastAlert]);

  const online = cameras.filter((c) => c.status === 'online').length;
  const newAlerts = alerts.filter((a) => a.status === 'new').length;

  return (
    <div className="page">
      <h1>Dashboard</h1>

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-value">{cameras.length}</span>
          <span className="stat-label">Cameras</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{online}</span>
          <span className="stat-label">Online</span>
        </div>
        <div className="stat-card stat-alert">
          <span className="stat-value">{newAlerts}</span>
          <span className="stat-label">New alerts</span>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>Cameras</h2>
          <Link to="/cameras">Manage →</Link>
        </div>
        <div className="camera-grid">
          {cameras.map((c) => (
            <Link key={c.id} to={`/cameras/${c.id}`} className="camera-tile">
              <div className="camera-tile-preview">📹</div>
              <div className="camera-tile-info">
                <strong>{c.name}</strong>
                <span className={`pill pill-${c.status === 'online' ? 'new' : 'dismissed'}`}>{c.status}</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Recent alerts</h2>
          <Link to="/alerts">View all →</Link>
        </div>
        <div className="alert-list">
          {alerts.length === 0 && <p className="empty-state">No alerts yet. Argus is watching.</p>}
          {alerts.map((a) => (
            <AlertCard key={a.id} alert={a} />
          ))}
        </div>
      </section>
    </div>
  );
}
