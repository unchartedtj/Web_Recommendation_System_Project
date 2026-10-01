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
 * protected endpoint. (Anyone can change browser code, but they can't fake a
 * server-checked token. That's why @role_required exists in Flask too.)
 *
 * Used in App.jsx like:
 *   <Route element={<ProtectedRoute allowedRoles={['student']} />}>
 *     <Route path="/student" element={<StudentDashboard />} />
 *   </Route>
 */
export default function ProtectedRoute({ allowedRoles }) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    // <Navigate> redirects as soon as it's drawn. `from` remembers where the user was heading.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={dashboardPathFor(user.role)} replace />;
  }
  // <Outlet> = "draw the child route here" (e.g. the StudentDashboard page).
  return <Outlet />;
}
