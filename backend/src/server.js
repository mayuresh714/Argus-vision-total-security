import 'dotenv/config';
import http from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { createApp } from './app.js';
import { setIo } from './ws/io.js';
import { startAllCameraLoops } from './services/scanPipeline.js';

const PORT = process.env.PORT || 4000;

const app = createApp();
const server = http.createServer(app);

const io = new SocketIOServer(server, {
  cors: { origin: process.env.CORS_ORIGIN || '*' },
});
setIo(io);

io.on('connection', (socket) => {
  socket.emit('connected', { ts: new Date().toISOString() });
});

server.listen(PORT, () => {
  console.log(`Argus backend listening on :${PORT}`);
  startAllCameraLoops();
});
