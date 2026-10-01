import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite is the tool that runs the development server (`npm run dev`) and builds the
// final files for going live (`npm run build` → the dist/ folder).
// The react() plugin lets Vite understand JSX.
// Port 5173 must match FRONTEND_ORIGIN in backend/.env (used for CORS).
// strictPort: fail instead of silently switching to another port if 5173 is busy.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
