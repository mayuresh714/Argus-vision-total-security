import { Link } from 'react-router-dom';
import ScoreBadge from './ScoreBadge.jsx';

export default function AlertCard({ alert }) {
  const time = new Date(alert.createdAt).toLocaleString();
  return (
    <Link to={`/alerts/${alert.id}`} className={`alert-card status-${alert.status}`}>
      <div className="alert-card-thumb">🎞️</div>
      <div className="alert-card-body">
        <div className="alert-card-top">
          <strong>{alert.cameraName}</strong>
          <ScoreBadge score={alert.score} />
        </div>
        <p className="alert-reason">{alert.reason}</p>
        <div className="alert-card-meta">
          <span>Tier {alert.finalTier}</span>
          <span>{time}</span>
          <span className={`pill pill-${alert.status}`}>{alert.status}</span>
        </div>
      </div>
    </Link>
  );
}
