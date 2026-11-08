/**
 * Student API calls: the profile (grades + skills + interests) and recommendations.
 * Each function matches one Flask endpoint (backend/app/students and app/recommendations).
 */
import client from './client.js';

/** GET /api/student/profile → { grades, skill_ids, sector_ids, profile_updated_at, is_complete } */
export async function fetchProfile() {
  const { data } = await client.get('/student/profile');
  return data.profile;
}

/**
 * PUT /api/student/profile: save everything and get fresh recommendations back.
 * Body: { grades: {unit_id: mark}, skill_ids: [...], sector_ids: [...], confirm_implausible? }
 * Errors: 400 = fields to fix, 409 = all marks identical (ask the student to confirm).
 */
export async function saveProfile(payload) {
  const { data } = await client.put('/student/profile', payload);
  return data; // { message, profile, recommendations }
}

/**
 * GET /api/recommendations →
 *   { eligible: [...], not_eligible: [...], profile_updated_at, generated_at, profile_complete }
 */
export async function fetchRecommendations() {
  const { data } = await client.get('/recommendations');
  return data;
}

/**
 * GET /api/opportunities?search=&sector_id=&skill_id=&sort= → { opportunities, sort, profile_complete }
 * Empty filters are left out of the URL.
 */
export async function fetchOpportunities(filters = {}) {
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '' && v != null));
  const { data } = await client.get('/opportunities', { params });
  return data;
}

/** GET /api/opportunities/:id → { opportunity, profile_complete, my_match? } */
export async function fetchOpportunity(id) {
  const { data } = await client.get(`/opportunities/${id}`);
  return data;
}

/**
 * POST /api/student/transcript: upload (or replace) my transcript PDF → status "pending".
 * Sent as a file upload (multipart form), not JSON.
 */
export async function uploadTranscript(file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await client.post('/student/transcript', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.transcript;
}

/** Open my uploaded transcript in a new tab (fetched with my login token). */
export async function openMyTranscript() {
  const response = await client.get('/student/transcript/file', { responseType: 'blob' });
  window.open(URL.createObjectURL(response.data), '_blank', 'noopener');
}
