import client from './client.js';

/** Active academic units: the only units partners may choose as requirements. */
export async function fetchUnits() {
  const { data } = await client.get('/units');
  return data.units;
}
