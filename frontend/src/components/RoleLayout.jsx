/**
 * Wraps a page shared by every role (Change password, Give feedback) in that role's own
 * layout, so the navbar the user is used to stays the same.
 */
import { useAuth } from '../context/AuthContext.jsx';
import { PARTNER_NAV } from '../pages/partner/partnerNav.js';
import { ROLES } from '../utils/roles.js';
import AdminLayout from './admin/AdminLayout.jsx';
import DashboardLayout from './DashboardLayout.jsx';
import StudentLayout from './student/StudentLayout.jsx';

export default function RoleLayout({ title, children }) {
  const { user } = useAuth();
  if (user?.role === ROLES.STUDENT) {
    return <StudentLayout><h1>{title}</h1>{children}</StudentLayout>;
  }
  if (user?.role === ROLES.ADMIN) return <AdminLayout title={title}>{children}</AdminLayout>;
  return (
    <DashboardLayout title="Industry partner dashboard" nav={PARTNER_NAV}>
      <h2>{title}</h2>
      {children}
    </DashboardLayout>
  );
}
