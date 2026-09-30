import client from './client.js';

// ---- Industry partner: own opportunities ----

export async function fetchMyOpportunities() {
  const { data } = await client.get('/partner/opportunities');
  return data.opportunities;
}

export async function fetchMyOpportunity(id) {
  const { data } = await client.get(`/partner/opportunities/${id}`);
  return data.opportunity;
}

export async function createOpportunity(payload) {
  const { data } = await client.post('/partner/opportunities', payload);
  return data.opportunity;
}

export async function updateOpportunity(id, payload) {
  const { data } = await client.put(`/partner/opportunities/${id}`, payload);
  return data.opportunity;
}

export async function closeOpportunity(id) {
  const { data } = await client.patch(`/partner/opportunities/${id}/close`);
  return data.opportunity;
}
