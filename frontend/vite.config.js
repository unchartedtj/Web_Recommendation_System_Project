/// <reference types="vitest" />
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
  // Put the chart library (used only on admin pages) and React in their own files, so the
  // main app file stays small and the browser can cache them separately.
  build: {
    rollupOptions: {
      output: {
        manualChunks: { charts: ['recharts'], react: ['react', 'react-dom', 'react-router-dom'] },
      },
    },
  },
  // Component tests (`npm test`): Vitest runs them in jsdom, a simulated browser.
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
});
