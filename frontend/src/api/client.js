/**
 * Shared axios instance. Every API call goes through here so the base URL,
 * JWT header and session-expiry handling live in one place.
 */
import axios from 'axios';

export const TOKEN_KEY = 'wbl_token';
export const USER_KEY = 'wbl_user';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
  headers: { 'Content-Type': 'application/json' },
});

// Attach the JWT (if any) to every outgoing request.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// An expired or invalid token on a protected call means the session is over.
// Clear it and send the user back to login. The /auth/login 401 ("wrong password")
// is excluded so the login form can show the error itself.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    if (error.response?.status === 401 && !url.includes('/auth/login')) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      if (window.location.pathname !== '/login') window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

/**
 * Normalise an axios error into the backend's {error, fields} shape,
 * including network failures where there is no response at all.
 */
export function parseApiError(error) {
  const data = error.response?.data;
  if (data && typeof data === 'object' && 'error' in data) {
    return { message: data.error, fields: data.fields || {} };
  }
  if (!error.response) {
    return { message: 'Cannot reach the server. Is the backend running?', fields: {} };
  }
  return { message: 'Something went wrong. Please try again.', fields: {} };
}

export default client;
