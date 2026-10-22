/**
 * Opportunity API calls for industry partners.
 * Each function matches one Flask endpoint in backend/app/opportunities/routes.py.
 */
import client from './client.js';

// ---- Industry partner: own opportunities ----

/** GET /api/partner/opportunities: my opportunities (open and closed). */
export async function fetchMyOpportunities() {
  const { data } = await client.get('/partner/opportunities');
  return data.opportunities;
}

/** GET /api/partner/opportunities/:id: one of mine, to fill the Edit form. */
export async function fetchMyOpportunity(id) {
  const { data } = await client.get(`/partner/opportunities/${id}`);
  return data.opportunity;
}

/** POST /api/partner/opportunities: create a new opportunity. */
export async function createOpportunity(payload) {
  const { data } = await client.post('/partner/opportunities', payload);
  return data.opportunity;
}

/** PUT /api/partner/opportunities/:id: save edits (details + requirements). */
export async function updateOpportunity(id, payload) {
  const { data } = await client.put(`/partner/opportunities/${id}`, payload);
  return data.opportunity;
}

/** PATCH /api/partner/opportunities/:id/close: close it. */
export async function closeOpportunity(id) {
  const { data } = await client.patch(`/partner/opportunities/${id}/close`);
  return data.opportunity;
}

// ---- Industry partner: candidates ----

/** GET /api/partner/opportunities/:id/candidates?status= → { opportunity, counts, candidates } */
export async function fetchCandidates(id, status) {
  const { data } = await client.get(`/partner/opportunities/${id}/candidates`,
    { params: status ? { status } : {} });
  return data;
}

/** PATCH /api/partner/applications/:id. Body: { action: shortlist|accept|reject, reason?, start_date?, end_date? } */
export async function decideApplication(id, body) {
  const { data } = await client.patch(`/partner/applications/${id}`, body);
  return data.application;
}
