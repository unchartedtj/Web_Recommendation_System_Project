/**
 * Page shell for every student page: a top navbar + the page content.
 *
 * Navbar links: Dashboard · Recommendations · Browse Internships · My Profile · Logout.
 * The current page is highlighted (NavLink adds class "active"). On small screens
 * (< 760px) the links collapse behind a "Menu" button.
 */
import { useEffect, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';

const LINKS = [
  { to: '/student', label: 'Dashboard', end: true },
  { to: '/student/recommendations', label: 'Recommendations' },
  { to: '/student/opportunities', label: 'Browse Internships' },
  { to: '/student/profile', label: 'My Profile' },
];

export default function StudentLayout({ children }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close the mobile menu whenever the page changes.
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="student-app">
      <header className="navbar">
        <span className="brand">WBL Placement</span>
        {/* Only visible on small screens; aria-expanded tells screen readers if it's open. */}
        <button type="button" className="navbar__toggle" aria-expanded={menuOpen}
          aria-controls="student-nav" onClick={() => setMenuOpen(!menuOpen)}>
          <span aria-hidden="true">☰</span> Menu
        </button>
        <nav id="student-nav" className={`navbar__links ${menuOpen ? 'navbar__links--open' : ''}`}
          aria-label="Student navigation">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>{link.label}</NavLink>
          ))}
          <button type="button" className="navbar__logout" onClick={handleLogout}>Logout</button>
        </nav>
      </header>
      <main className="student-main">{children}</main>
    </div>
  );
}
