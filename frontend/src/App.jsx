/**
 * The app's page map: which URL shows which page.
 *
 * react-router-dom reads the URL in the address bar and renders the matching <Route>.
 * No full page reload happens when you move between pages; React just swaps components.
 */
import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import AdminActivity from './pages/admin/AdminActivity.jsx';
import AdminCatalog from './pages/admin/AdminCatalog.jsx';
import AdminModel from './pages/admin/AdminModel.jsx';
import AdminOpportunities from './pages/admin/AdminOpportunities.jsx';
import AdminOpportunityEditor from './pages/admin/AdminOpportunityEditor.jsx';
import AdminOverview from './pages/admin/AdminOverview.jsx';
import { AdminPartnerDetail, AdminPartners } from './pages/admin/AdminPartners.jsx';
import AdminPlacements from './pages/admin/AdminPlacements.jsx';
import AdminReports from './pages/admin/AdminReports.jsx';
import AdminStudentDetail from './pages/admin/AdminStudentDetail.jsx';
import AdminStudents from './pages/admin/AdminStudents.jsx';
import AdminUsers from './pages/admin/AdminUsers.jsx';
import ChangePassword from './pages/ChangePassword.jsx';
import Contact from './pages/Contact.jsx';
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
import { ROLES } from './utils/roles.js';

/** Sends an old detail address (e.g. /admin/students/7) to its new place. */
function OldAdminRedirect({ to }) {
  const { id } = useParams();
  return <Navigate to={`${to}/${id}`} replace />;
}

export default function App() {
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
        {/* People */}
        <Route path="/admin/people/students" element={<AdminStudents />} />
        <Route path="/admin/people/students/:id" element={<AdminStudentDetail />} />
        <Route path="/admin/people/partners" element={<AdminPartners />} />
        <Route path="/admin/people/partners/:id" element={<AdminPartnerDetail />} />
        <Route path="/admin/people/accounts" element={<AdminUsers />} />
        {/* Internships */}
        <Route path="/admin/internships/opportunities" element={<AdminOpportunities />} />
        <Route path="/admin/internships/opportunities/new" element={<AdminOpportunityEditor />} />
        <Route path="/admin/internships/opportunities/:id/edit" element={<AdminOpportunityEditor />} />
        <Route path="/admin/internships/catalog" element={<AdminCatalog />} />
        {/* Reports & settings */}
        <Route path="/admin/reports/summary" element={<AdminReports />} />
        <Route path="/admin/reports/activity" element={<AdminActivity />} />
        <Route path="/admin/reports/model" element={<AdminModel />} />
        {/* A section name on its own opens its first tab; older addresses still work. */}
        <Route path="/admin/people" element={<Navigate to="/admin/people/students" replace />} />
        <Route path="/admin/internships" element={<Navigate to="/admin/internships/opportunities" replace />} />
        <Route path="/admin/reports" element={<Navigate to="/admin/reports/summary" replace />} />
        <Route path="/admin/students" element={<Navigate to="/admin/people/students" replace />} />
        <Route path="/admin/students/:id" element={<OldAdminRedirect to="/admin/people/students" />} />
        <Route path="/admin/partners" element={<Navigate to="/admin/people/partners" replace />} />
        <Route path="/admin/partners/:id" element={<OldAdminRedirect to="/admin/people/partners" />} />
        <Route path="/admin/users" element={<Navigate to="/admin/people/accounts" replace />} />
        <Route path="/admin/opportunities" element={<Navigate to="/admin/internships/opportunities" replace />} />
        <Route path="/admin/catalog" element={<Navigate to="/admin/internships/catalog" replace />} />
        <Route path="/admin/activity" element={<Navigate to="/admin/reports/activity" replace />} />
        <Route path="/admin/model" element={<Navigate to="/admin/reports/model" replace />} />
      </Route>

      {/* Every logged-in role. */}
      <Route element={<ProtectedRoute />}>
        <Route path="/account/password" element={<ChangePassword />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.STUDENT, ROLES.PARTNER]} />}>
        <Route path="/contact" element={<Contact />} />
      </Route>

      {/* "/" is the public landing page (logged-in users go to their dashboard);
          any other unknown URL shows the 404 page. */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
