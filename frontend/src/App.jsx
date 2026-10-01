/**
 * The app's page map: which URL shows which page.
 *
 * react-router-dom reads the URL in the address bar and renders the matching <Route>.
 * No full page reload happens when you move between pages; React just swaps components.
 */
import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import { useAuth } from './context/AuthContext.jsx';
import AdminDashboard from './pages/AdminDashboard.jsx';
import Login from './pages/Login.jsx';
import MyOpportunities from './pages/partner/MyOpportunities.jsx';
import OpportunityEditor from './pages/partner/OpportunityEditor.jsx';
import Register from './pages/Register.jsx';
import StudentDashboard from './pages/StudentDashboard.jsx';
import { ROLES, dashboardPathFor } from './utils/roles.js';

export default function App() {
  // The logged-in user (or null), shared app-wide by AuthContext.
  const { user } = useAuth();
  // "/" and unknown paths go to the user's dashboard if logged in, otherwise to login.
  const home = user ? dashboardPathFor(user.role) : '/login';

  return (
    <Routes>
      {/* Public pages: anyone can open these. */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected pages. A <Route> with no path wraps its children: ProtectedRoute
          runs first and only shows the child page if the user is logged in with an
          allowed role. */}
      <Route element={<ProtectedRoute allowedRoles={[ROLES.STUDENT]} />}>
        <Route path="/student" element={<StudentDashboard />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.PARTNER]} />}>
        {/* The partner dashboard home is the "My Opportunities" list. */}
        <Route path="/partner" element={<MyOpportunities />} />
        <Route path="/partner/opportunities/new" element={<OpportunityEditor />} />
        {/* ":id" is a URL parameter, e.g. /partner/opportunities/7/edit gives id = "7". */}
        <Route path="/partner/opportunities/:id/edit" element={<OpportunityEditor />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.ADMIN]} />}>
        <Route path="/admin" element={<AdminDashboard />} />
      </Route>

      {/* "*" matches any other URL: redirect to the right home page. */}
      <Route path="*" element={<Navigate to={home} replace />} />
    </Routes>
  );
}
