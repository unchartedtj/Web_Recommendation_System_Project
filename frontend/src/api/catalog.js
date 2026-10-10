/**
 * The preset lists: technical skills and sectors (career interests / internship sectors).
 * Used by the partner's opportunity form and the student's profile.
 */
import client from './client.js';

/** GET /api/skills → [{ category, skills: [{ skill_id, name }] }], grouped by category. */
export async function fetchSkillCategories() {
  const { data } = await client.get('/skills');
  return data.categories;
}

/** GET /api/sectors → [{ sector_id, name }] */
export async function fetchSectors() {
  const { data } = await client.get('/sectors');
  return data.sectors;
}
