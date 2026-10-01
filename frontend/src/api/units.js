/** Unit catalogue API call. */
import client from './client.js';

/** GET /api/units: active academic units, the only units partners may choose as requirements. */
export async function fetchUnits() {
  const { data } = await client.get('/units');
  return data.units;   // [{ unit_id, unit_name }, ...]
}
