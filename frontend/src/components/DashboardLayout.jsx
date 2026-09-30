import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

/**
 * Shared shell for dashboards: header, greeting, optional section nav, and logout.
 * `nav` is a list of {to, label} links shown under the greeting.
 */
export default function DashboardLayout({ title, nav, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="dashboard">
      <header className="topbar">
        <span className="brand">WBL Placement</span>
        <button type="button" className="btn btn--ghost" onClick={handleLogout}>
          Logout
        </button>
      </header>
      <main className="dashboard__body">
        <p className="eyebrow">{title}</p>
        <h1>Welcome, {user?.name}</h1>
        {nav && (
          <nav className="subnav">
            {nav.map((link) => (
              // `end` so "/partner" isn't highlighted while on "/partner/opportunities/new".
              <NavLink key={link.to} to={link.to} end>
                {link.label}
              </NavLink>
            ))}
          </nav>
        )}
        {children}
      </main>
    </div>
  );
}
