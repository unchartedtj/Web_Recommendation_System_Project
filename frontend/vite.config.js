import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Port 5173 must match FRONTEND_ORIGIN in backend/.env (used for CORS).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
