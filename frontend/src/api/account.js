/**
 * Account and feedback API calls for every logged-in user.
 */
import client from './client.js';

/** POST /api/auth/change-password { current_password, new_password, confirm_password } → user */
export async function changePassword(payload) {
  const { data } = await client.post('/auth/change-password', payload);
  return data.user;
}

/** GET /api/sus/questions → { questions: [10 statements], scale: [5 labels] } */
export async function fetchSusQuestions() {
  const { data } = await client.get('/sus/questions');
  return data;
}

/** GET /api/sus/mine → my saved answers, or null */
export async function fetchMySus() {
  const { data } = await client.get('/sus/mine');
  return data.response;
}

/** PUT /api/sus { q1..q10, comments? } → { message } (the score is never returned) */
export async function submitSus(payload) {
  const { data } = await client.put('/sus', payload);
  return data;
}
