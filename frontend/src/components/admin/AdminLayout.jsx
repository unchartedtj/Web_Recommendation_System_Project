/**
 * Page shell for every admin page: a top bar (brand + account menu), a sidebar with the
 * 5 admin sections, and, inside a grouped section, tabs for its pages:
 *
 *   Dashboard · Placements
 *   People              → Students · Partners · All accounts
 *   Internships         → Opportunities · Catalog
 *   Reports & settings  → Activity log · Model
 *
 * Below 760px the sidebar collapses behind a "Menu" button.
 */
import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import AccountMenu from '../AccountMenu.jsx';

const SECTIONS = [
  { to: '/admin', label: 'Dashboard', icon: '📊', end: true },
  { to: '/admin/placements', label: 'Placements', icon: '🎓' },
  { to: '/admin/people', label: 'People', icon: '👥', tabs: [
    { to: '/admin/people/students', label: 'Students' },
    { to: '/admin/people/partners', label: 'Partners' },
    { to: '/admin/people/accounts', label: 'All accounts' },
  ] },
  { to: '/admin/internships', label: 'Internships', icon: '💼', tabs: [
    { to: '/admin/internships/opportunities', label: 'Opportunities' },
    { to: '/admin/internships/catalog', label: 'Catalog' },
  ] },
  { to: '/admin/reports', label: 'Reports & settings', icon: '📈', tabs: [
    { to: '/admin/reports/activity', label: 'Activity log' },
    { to: '/admin/reports/model', label: 'Model' },
  ] },
];

export default function AdminLayout({ title, actions, children }) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  // The grouped section this page belongs to (if any), so its tabs can be shown.
  const section = SECTIONS.find((s) => s.tabs && location.pathname.startsWith(`${s.to}/`));

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
          {SECTIONS.map((s) => (
            <NavLink key={s.to} to={s.tabs ? s.tabs[0].to : s.to} end={s.end}
              className={({ isActive }) => (isActive || section === s ? 'active' : '')}>
              <span aria-hidden="true">{s.icon} </span>{s.label}
            </NavLink>
          ))}
        </nav>
        <main className="admin-main">
          {section && (
            <nav className="admin-tabs" aria-label={`${section.label} pages`}>
              {section.tabs.map((t) => <NavLink key={t.to} to={t.to}>{t.label}</NavLink>)}
            </nav>
          )}
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
