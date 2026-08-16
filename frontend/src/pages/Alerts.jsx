import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useSocket } from '../context/SocketContext.jsx';
import AlertCard from '../components/AlertCard.jsx';

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'new', label: 'New' },
  { key: 'acknowledged', label: 'Acknowledged' },
  { key: 'dismissed', label: 'Dismissed' },
];

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState('');
  const { lastAlert } = useSocket();

  async function load() {
    const { alerts } = await api.listAlerts(status ? { status } : {});
    setAlerts(alerts);
  }

  useEffect(() => {
    load();
  }, [status]);

  useEffect(() => {
    if (lastAlert) load();
  }, [lastAlert]);

  return (
    <div className="page">
      <h1>Alerts</h1>
      <div className="filter-row">
        {FILTERS.map((f) => (
          <button key={f.key} className={`chip ${status === f.key ? 'chip-active' : ''}`} onClick={() => setStatus(f.key)}>
            {f.label}
          </button>
        ))}
      </div>
      <div className="alert-list">
        {alerts.length === 0 && <p className="empty-state">No alerts match this filter.</p>}
        {alerts.map((a) => (
          <AlertCard key={a.id} alert={a} />
        ))}
      </div>
    </div>
  );
}
