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
  const { user } = useAuth();
  // "/" and unknown paths go to the user's dashboard if logged in, otherwise to login.
  const home = user ? dashboardPathFor(user.role) : '/login';

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<ProtectedRoute allowedRoles={[ROLES.STUDENT]} />}>
        <Route path="/student" element={<StudentDashboard />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.PARTNER]} />}>
        {/* The partner dashboard home is the "My Opportunities" list. */}
        <Route path="/partner" element={<MyOpportunities />} />
        <Route path="/partner/opportunities/new" element={<OpportunityEditor />} />
        <Route path="/partner/opportunities/:id/edit" element={<OpportunityEditor />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.ADMIN]} />}>
        <Route path="/admin" element={<AdminDashboard />} />
      </Route>

      <Route path="*" element={<Navigate to={home} replace />} />
    </Routes>
  );
}
