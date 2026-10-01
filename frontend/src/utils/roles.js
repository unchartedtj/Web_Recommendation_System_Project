// Role values must match the backend's users.role enum.
// Using ROLES.STUDENT instead of typing 'student' everywhere prevents typos.
export const ROLES = {
  STUDENT: 'student',
  PARTNER: 'industry_partner',
  ADMIN: 'system_admin',
};

// Which page each role lands on after logging in.
// [ROLES.STUDENT] in square brackets means "use the VALUE of ROLES.STUDENT as the key".
const DASHBOARD_PATHS = {
  [ROLES.STUDENT]: '/student',
  [ROLES.PARTNER]: '/partner',
  [ROLES.ADMIN]: '/admin',
};

/** e.g. dashboardPathFor('industry_partner') → '/partner'. Unknown role → '/login'. */
export function dashboardPathFor(role) {
  return DASHBOARD_PATHS[role] ?? '/login';
}
