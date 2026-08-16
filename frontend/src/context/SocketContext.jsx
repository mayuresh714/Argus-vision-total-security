import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';
import { useAuth } from './AuthContext.jsx';

const SocketContext = createContext(null);

export function SocketProvider({ children }) {
  const { user } = useAuth();
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [lastAlert, setLastAlert] = useState(null);
  const [liveTiers, setLiveTiers] = useState([]); // recent scan-tier events, capped

  useEffect(() => {
    if (!user) return undefined;
    const socket = io('/', { path: '/socket.io' });
    socketRef.current = socket;

    socket.on('connect', () => setConnected(true));
    socket.on('disconnect', () => setConnected(false));
    socket.on('alert:new', ({ alert }) => setLastAlert(alert));
    socket.on('scan:tier', (evt) => {
      setLiveTiers((prev) => [evt, ...prev].slice(0, 50));
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [user]);

  return (
    <SocketContext.Provider value={{ connected, lastAlert, liveTiers, socket: socketRef.current }}>
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  const ctx = useContext(SocketContext);
  if (!ctx) throw new Error('useSocket must be used within SocketProvider');
  return ctx;
}
