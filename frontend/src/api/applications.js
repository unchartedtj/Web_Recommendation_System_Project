/**
 * Student application API calls (backend/app/applications/routes.py).
 */
import client from './client.js';

/**
 * POST /api/applications. Body: { opportunity_id, motivation_note?, acknowledge_below_minimum? }
 * 409 = a rule blocked it (e.g. below minimum → the reply lists unmet_requirements).
 */
export async function applyToOpportunity(payload) {
  const { data } = await client.post('/applications', payload);
  return data.application;
}

/** GET /api/applications/mine?status= → the student's applications (+ placement if accepted). */
export async function fetchMyApplications(status) {
  const { data } = await client.get('/applications/mine', { params: status ? { status } : {} });
  return data.applications;
}

/** PATCH /api/applications/:id/withdraw */
export async function withdrawApplication(id) {
  const { data } = await client.patch(`/applications/${id}/withdraw`);
  return data.application;
}
