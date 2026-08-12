import { io, Socket } from 'socket.io-client';

function getSocketUrl(): string {
  if (process.env.NEXT_PUBLIC_SOCKET_URL) {
    return process.env.NEXT_PUBLIC_SOCKET_URL;
  }
  if (typeof window !== 'undefined') {
    // In production Vercel, connect to current host origin if local WS is not specified
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      return window.location.origin;
    }
  }
  return 'http://localhost:5000';
}

let socket: Socket | null = null;

export const getSocket = (): Socket => {
  if (!socket) {
    const isProdBrowser = typeof window !== 'undefined' && 
      window.location.hostname !== 'localhost' && 
      window.location.hostname !== '127.0.0.1';

    socket = io(getSocketUrl(), {
      autoConnect: !isProdBrowser, // Disable aggressive autoConnect to localhost in production Vercel
      transports: ['polling', 'websocket'],
      reconnectionAttempts: 3,
      reconnectionDelay: 5000,
      timeout: 3000,
    });
  }
  return socket;
};
