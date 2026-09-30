import client from './client.js';

export async function register(payload) {
  const { data } = await client.post('/auth/register', payload);
  return data; // { message, user }
}

export async function login(email, password) {
  const { data } = await client.post('/auth/login', { email, password });
  return data; // { access_token, user }
}

export async function fetchMe() {
  const { data } = await client.get('/auth/me');
  return data.user;
}
