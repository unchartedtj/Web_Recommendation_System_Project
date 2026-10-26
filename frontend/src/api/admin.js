/**
 * System admin API calls (backend/app/admin/*). Lists are paginated:
 * { items, page, per_page, total, pages }. Empty filter values are left out of the URL.
 */
import client from './client.js';

const clean = (params = {}) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined));

async function get(url, params) {
  const { data } = await client.get(url, { params: clean(params) });
  return data;
}

// ---- Overview, activity ----
export const fetchOverview = () => get('/admin/overview');
export const fetchActivity = (params) => get('/admin/activity', params);

// ---- Placements (TC09) ----
export const fetchPlacements = (params) => get('/admin/placements', params);
export const fetchPlacement = (id) => get(`/admin/placements/${id}`).then((d) => d.placement);
export async function updatePlacement(id, body) {
  const { data } = await client.patch(`/admin/placements/${id}`, body);
  return data.placement;
}

// ---- Records ----
export const fetchStudents = (params) => get('/admin/students', params);
export const fetchStudent = (id) => get(`/admin/students/${id}`).then((d) => d.student);
export const fetchPartners = (params) => get('/admin/partners', params);
export const fetchPartner = (id) => get(`/admin/partners/${id}`).then((d) => d.partner);
export const fetchAdminOpportunities = (params) => get('/admin/opportunities', params);
export async function setOpportunityOpen(id, open) {
  const { data } = await client.patch(`/admin/opportunities/${id}/${open ? 'reopen' : 'close'}`);
  return data.opportunity;
}

// ---- Users ----
export const fetchUsers = (params) => get('/admin/users', params);
export const fetchUserImpact = (id) => get(`/admin/users/${id}/impact`);
export async function setUserActive(id, active) {
  const { data } = await client.patch(`/admin/users/${id}/${active ? 'activate' : 'deactivate'}`);
  return data;
}
export async function resetUserPassword(id, temporaryPassword) {
  const { data } = await client.post(`/admin/users/${id}/reset-password`,
    temporaryPassword ? { temporary_password: temporaryPassword } : {});
  return data;   // { temporary_password, user }
}
export async function createAdmin(body) {
  const { data } = await client.post('/admin/admins', body);
  return data.user;
}

// ---- Catalogue: kind = 'skills' | 'sectors' | 'units' ----
export const fetchCatalog = (kind) => get(`/admin/${kind}`);
export async function createCatalogItem(kind, body) {
  const { data } = await client.post(`/admin/${kind}`, body);
  return data;
}
export async function updateCatalogItem(kind, id, body) {
  const { data } = await client.put(`/admin/${kind}/${id}`, body);
  return data;
}

// ---- Model, SUS ----
export const fetchModel = () => get('/admin/model');
export async function retrainModel() {
  const { data } = await client.post('/admin/model/retrain');
  return data;
}
export const fetchSusResults = () => get('/admin/sus');

/**
 * Download a CSV export. The request goes through axios (so the login token is sent),
 * then the browser is asked to save the file.
 */
export async function downloadCsv(url, filename, params) {
  const response = await client.get(url, { params: clean(params), responseType: 'blob' });
  const href = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}
