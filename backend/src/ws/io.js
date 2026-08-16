let ioInstance = null;

export function setIo(io) {
  ioInstance = io;
}

export function getIo() {
  return ioInstance;
}

export function emit(event, payload) {
  if (ioInstance) ioInstance.emit(event, payload);
}
