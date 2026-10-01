/**
 * The React entry point: the first file that runs in the browser.
 * index.html has an empty <div id="root"></div>, and React draws the whole app inside it.
 *
 * The wrappers, from outside in:
 *   StrictMode    – extra development-time warnings (no effect in production)
 *   BrowserRouter – enables page URLs (/login, /partner, ...) without full reloads
 *   AuthProvider  – shares the logged-in user with every component (see AuthContext.jsx)
 *   App           – the page map (see App.jsx)
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import './styles/global.css';   // importing a CSS file applies it to the whole app

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
