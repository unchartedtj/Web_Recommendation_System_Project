import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { dashboardPathFor } from '../utils/roles.js';

/**
 * Guards nested routes.
 * - Not logged in → /login.
 * - Logged in with the wrong role (e.g. a student opening /admin) → the user's own
 *   dashboard, so they never see another role's pages.
 *
 * Note: this is a UX guard only. The backend must still check roles on every
 * protected endpoint.
 */
export default function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={dashboardPathFor(user.role)} replace />;
  }
  return <Outlet />;
}
