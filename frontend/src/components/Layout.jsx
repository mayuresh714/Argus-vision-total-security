import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useSocket } from '../context/SocketContext.jsx';

const NAV = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/cameras', label: 'Cameras', icon: '📷' },
  { to: '/alerts', label: 'Alerts', icon: '🚨' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { connected } = useSocket();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-eye">👁️</span>
          <span>Argus</span>
        </div>
        <div className="topbar-right">
          <span className={`status-dot ${connected ? 'online' : 'offline'}`} title={connected ? 'Live' : 'Disconnected'} />
          <span className="user-name">{user?.name}</span>
          <button className="btn-ghost" onClick={logout}>Sign out</button>
        </div>
      </header>

      <div className="app-body">
        <nav className="sidebar">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <main className="content">
          <Outlet />
        </main>
      </div>

      <nav className="bottom-nav">
        {NAV.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
