/**
 * Page shell for every admin page: a top bar (brand + account menu) and a sidebar with the
 * 10 admin sections. Below 760px the sidebar collapses behind a "Menu" button.
 */
import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import AccountMenu from '../AccountMenu.jsx';

const ADMIN_LINKS = [
  { to: '/admin', label: 'Overview', icon: '📊', end: true },
  { to: '/admin/placements', label: 'Placements', icon: '🎓' },
  { to: '/admin/students', label: 'Students', icon: '🧑‍🎓' },
  { to: '/admin/partners', label: 'Partners', icon: '🏢' },
  { to: '/admin/opportunities', label: 'Opportunities', icon: '💼' },
  { to: '/admin/users', label: 'Users', icon: '👥' },
  { to: '/admin/catalog', label: 'Catalog', icon: '🗂' },
  { to: '/admin/model', label: 'Model', icon: '🧠' },
  { to: '/admin/sus', label: 'SUS Results', icon: '📝' },
  { to: '/admin/activity', label: 'Activity Log', icon: '🕑' },
];

export default function AdminLayout({ title, actions, children }) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  return (
    <div className="admin-app">
      <header className="navbar admin-topbar">
        <span className="brand">WBL Placement · Admin</span>
        <button type="button" className="navbar__toggle admin-menu-toggle" aria-expanded={menuOpen}
          aria-controls="admin-nav" onClick={() => setMenuOpen(!menuOpen)}>
          <span aria-hidden="true">☰</span> Menu
        </button>
        <AccountMenu />
      </header>
      <div className="admin-body">
        <nav id="admin-nav" aria-label="Admin sections"
          className={`admin-sidebar ${menuOpen ? 'admin-sidebar--open' : ''}`}>
          {ADMIN_LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>
              <span aria-hidden="true">{l.icon} </span>{l.label}
            </NavLink>
          ))}
        </nav>
        <main className="admin-main">
          {(title || actions) && (
            <div className="page-head">
              {title && <h1>{title}</h1>}
              {actions && <div className="page-head__actions">{actions}</div>}
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
