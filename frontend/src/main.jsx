/**
 * The React entry point: the first file that runs in the browser.
 * index.html has an empty <div id="root"></div>, and React draws the whole app inside it.
 *
 * The wrappers, from outside in:
 *   StrictMode    – extra development-time warnings (no effect in production)
 *   BrowserRouter – enables page URLs (/login, /partner, ...) without full reloads
 *   AuthProvider  – shares the logged-in user with every component (see AuthContext.jsx)
 *   ErrorBoundary – shows "Something went wrong" instead of a blank page if a page crashes
 *   App           – the page map (see App.jsx)
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import './styles/global.css';   // importing a CSS file applies it to the whole app
import './styles/admin.css';    // account menu, account pages and the admin dashboard

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* future flags: opt in to React Router v7 behaviour now (silences upgrade warnings). */}
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
