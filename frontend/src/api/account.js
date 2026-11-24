/**
 * Account API calls for every logged-in user.
 */
import client from './client.js';

/** POST /api/auth/change-password { current_password, new_password, confirm_password } → user */
export async function changePassword(payload) {
  const { data } = await client.post('/auth/change-password', payload);
  return data.user;
}

