/**
 * Shared axios instance. Every API call goes through here so the base URL,
 * JWT header and session-expiry handling live in one place.
 *
 * axios is a library for sending HTTP requests from the browser to the Flask API.
 * An "interceptor" is a function that runs on EVERY request (before it's sent) or on
 * every response (before your code sees it).
 */
import axios from 'axios';

// The names the token and user are saved under in the browser's localStorage.
export const TOKEN_KEY = 'wbl_token';
export const USER_KEY = 'wbl_user';

const client = axios.create({
  // Where the Flask API lives. VITE_API_URL can be set in frontend/.env (e.g. when
  // going live); otherwise the local development address is used.
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
  headers: { 'Content-Type': 'application/json' },   // we always send JSON
});

// Attach the JWT (if any) to every outgoing request.
// So API modules never have to add "Authorization: Bearer <token>" themselves.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// An expired or invalid token on a protected call means the session is over.
// Clear it and send the user back to login. The /auth/login 401 ("wrong password")
// is excluded so the login form can show the error itself.
client.interceptors.response.use(
  (response) => response,          // successful responses pass straight through
  (error) => {
    const url = error.config?.url || '';
    if (error.response?.status === 401 && !url.includes('/auth/login')) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      // A full page load to /login also resets all in-memory React state.
      if (window.location.pathname !== '/login') window.location.assign('/login');
    }
    // Re-throw so the calling code's `catch` still runs.
    return Promise.reject(error);
  },
);

/**
 * Normalise an axios error into the backend's {error, fields} shape,
 * including network failures where there is no response at all.
 * Pages call this in their `catch` blocks and get { message, fields } back.
 */
export function parseApiError(error) {
  const data = error.response?.data;
  // Our Flask API always replies with {"error": ..., "fields": {...}}.
  if (data && typeof data === 'object' && 'error' in data) {
    return { message: data.error, fields: data.fields || {} };
  }
  // No response at all = the request never reached the server (backend not running, no internet).
  if (!error.response) {
    return { message: 'Cannot reach the server. Is the backend running?', fields: {} };
  }
  return { message: 'Something went wrong. Please try again.', fields: {} };
}

export default client;
