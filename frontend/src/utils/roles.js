// Role values must match the backend's users.role enum.
export const ROLES = {
  STUDENT: 'student',
  PARTNER: 'industry_partner',
  ADMIN: 'system_admin',
};

const DASHBOARD_PATHS = {
  [ROLES.STUDENT]: '/student',
  [ROLES.PARTNER]: '/partner',
  [ROLES.ADMIN]: '/admin',
};

export function dashboardPathFor(role) {
  return DASHBOARD_PATHS[role] ?? '/login';
}
