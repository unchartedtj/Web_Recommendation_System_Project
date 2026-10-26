/**
 * Shown for any URL that doesn't exist.
 */
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { dashboardPathFor } from '../utils/roles.js';

export default function NotFound() {
  const { user } = useAuth();
  const home = user ? dashboardPathFor(user.role) : '/login';
  return (
    <div className="auth-page">
      <div className="card status-page">
        <p className="status-page__code" aria-hidden="true">404</p>
        <h1>Page not found</h1>
        <p className="muted">The page you were looking for doesn&apos;t exist or has moved.</p>
        <Link className="btn btn--primary" to={home}>{user ? 'Go to my dashboard' : 'Go to sign in'}</Link>
      </div>
    </div>
  );
}
