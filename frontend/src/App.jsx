/**
 * The app's page map: which URL shows which page.
 *
 * react-router-dom reads the URL in the address bar and renders the matching <Route>.
 * No full page reload happens when you move between pages; React just swaps components.
 */
import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import { useAuth } from './context/AuthContext.jsx';
import AdminActivity from './pages/admin/AdminActivity.jsx';
import AdminCatalog from './pages/admin/AdminCatalog.jsx';
import AdminModel from './pages/admin/AdminModel.jsx';
import AdminOpportunities from './pages/admin/AdminOpportunities.jsx';
import AdminOverview from './pages/admin/AdminOverview.jsx';
import { AdminPartnerDetail, AdminPartners } from './pages/admin/AdminPartners.jsx';
import AdminPlacements from './pages/admin/AdminPlacements.jsx';
import AdminStudentDetail from './pages/admin/AdminStudentDetail.jsx';
import AdminStudents from './pages/admin/AdminStudents.jsx';
import AdminSus from './pages/admin/AdminSus.jsx';
import AdminUsers from './pages/admin/AdminUsers.jsx';
import ChangePassword from './pages/ChangePassword.jsx';
import Feedback from './pages/Feedback.jsx';
import Login from './pages/Login.jsx';
import NotFound from './pages/NotFound.jsx';
import Candidates from './pages/partner/Candidates.jsx';
import MyOpportunities from './pages/partner/MyOpportunities.jsx';
import OpportunityEditor from './pages/partner/OpportunityEditor.jsx';
import Register from './pages/Register.jsx';
import StudentDashboard from './pages/StudentDashboard.jsx';
import BrowseOpportunities from './pages/student/BrowseOpportunities.jsx';
import MyApplications from './pages/student/MyApplications.jsx';
import OpportunityDetails from './pages/student/OpportunityDetails.jsx';
import StudentProfile from './pages/student/StudentProfile.jsx';
import StudentRecommendations from './pages/student/StudentRecommendations.jsx';
import { ROLES, dashboardPathFor } from './utils/roles.js';

function HomeRedirect({ home }) {
  return <Navigate to={home} replace />;
}

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
        <Route path="/student/profile" element={<StudentProfile />} />
        <Route path="/student/recommendations" element={<StudentRecommendations />} />
        <Route path="/student/opportunities" element={<BrowseOpportunities />} />
        <Route path="/student/opportunities/:id" element={<OpportunityDetails />} />
        <Route path="/student/applications" element={<MyApplications />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.PARTNER]} />}>
        {/* The partner dashboard home is the "My Opportunities" list. */}
        <Route path="/partner" element={<MyOpportunities />} />
        <Route path="/partner/opportunities/new" element={<OpportunityEditor />} />
        {/* ":id" is a URL parameter, e.g. /partner/opportunities/7/edit gives id = "7". */}
        <Route path="/partner/opportunities/:id/edit" element={<OpportunityEditor />} />
        <Route path="/partner/opportunities/:id/candidates" element={<Candidates />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.ADMIN]} />}>
        <Route path="/admin" element={<AdminOverview />} />
        <Route path="/admin/placements" element={<AdminPlacements />} />
        <Route path="/admin/students" element={<AdminStudents />} />
        <Route path="/admin/students/:id" element={<AdminStudentDetail />} />
        <Route path="/admin/partners" element={<AdminPartners />} />
        <Route path="/admin/partners/:id" element={<AdminPartnerDetail />} />
        <Route path="/admin/opportunities" element={<AdminOpportunities />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/catalog" element={<AdminCatalog />} />
        <Route path="/admin/model" element={<AdminModel />} />
        <Route path="/admin/sus" element={<AdminSus />} />
        <Route path="/admin/activity" element={<AdminActivity />} />
      </Route>

      {/* Every logged-in role. */}
      <Route element={<ProtectedRoute />}>
        <Route path="/account/password" element={<ChangePassword />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.STUDENT, ROLES.PARTNER]} />}>
        <Route path="/feedback" element={<Feedback />} />
      </Route>

      {/* "/" goes to the user's home page; any other unknown URL shows the 404 page. */}
      <Route path="/" element={<HomeRedirect home={home} />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
