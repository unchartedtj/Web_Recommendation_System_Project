/**
 * The preset lists: academic units, technical skills, sectors (career interests /
 * internship sectors) and counties. Used by the partner's opportunity form and the
 * student's profile.
 */
import client from './client.js';

/** GET /api/units: active academic units (the only units partners may choose as requirements). */
export async function fetchUnits() {
  const { data } = await client.get('/units');
  return data.units;   // [{ unit_id, unit_name }, ...]
}

/** GET /api/skills → [{ category, skills: [{ skill_id, name }] }], grouped by category. */
export async function fetchSkillCategories() {
  const { data } = await client.get('/skills');
  return data.categories;
}

/** GET /api/counties → Kenya's 47 counties, alphabetical (the Location dropdown). */
export async function fetchCounties() {
  const { data } = await client.get('/counties');
  return data.counties;
}

/** GET /api/sectors → [{ sector_id, name }] */
export async function fetchSectors() {
  const { data } = await client.get('/sectors');
  return data.sectors;
}
