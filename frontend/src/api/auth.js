/**
 * Auth API calls. Each function sends one request to Flask and returns the useful
 * part of the reply. The JWT header is added automatically by client.js.
 * If the server replies with an error, axios throws, and the caller's `catch` handles it.
 */
import client from './client.js';

/** POST /api/auth/register: create a student or partner account. */
export async function register(payload) {
  const { data } = await client.post('/auth/register', payload);   // `data` = the JSON body
  return data; // { message, user }
}

/** POST /api/auth/login: returns the token and the user's details. */
export async function login(email, password) {
  const { data } = await client.post('/auth/login', { email, password });
  return data; // { access_token, user }
}

/** GET /api/auth/me: who is logged in (used to refresh the user on page load). */
export async function fetchMe() {
  const { data } = await client.get('/auth/me');
  return data.user;
}
