/**
 * The public landing page ("/"), shown before logging in: what the portal is for, why
 * Work-Based Learning matters, and the key attachment requirements.
 * Logged-in users are sent straight to their own dashboard instead.
 */
import { Link, Navigate } from 'react-router-dom';
import Logo from '../components/Logo.jsx';
import WblRequirements from '../components/WblRequirements.jsx';
import { WHY_WBL } from '../content/wbl.js';
import { useAuth } from '../context/AuthContext.jsx';
import { dashboardPathFor } from '../utils/roles.js';

export default function Landing() {
  const { isAuthenticated, user } = useAuth();
  if (isAuthenticated) return <Navigate to={dashboardPathFor(user.role)} replace />;

  return (
    <div className="landing">
      <header className="landing__header">
        <div className="landing__container landing__header-inner">
          <div className="landing__identity">
            <Logo size="sm" className="landing__logo" />
            <div>
              <p className="landing__university">Strathmore University</p>
              <p className="landing__school">School of Computing and Engineering Sciences</p>
            </div>
          </div>
          <Link className="landing__login-link" to="/login">Log in</Link>
        </div>
      </header>

      <main className="landing__container landing__main">
        <section className="landing__intro" aria-labelledby="hero-title">
          <h1 id="hero-title">Welcome to the WBL Placement Portal</h1>
          <p className="landing__lead">
            Find the Work-Based Learning placement that fits your grades, skills and career interests.
          </p>
          <div className="landing__actions">
            <Link className="btn btn--primary" to="/login">Log in</Link>
            <Link className="btn btn--secondary" to="/register">Create an account</Link>
          </div>

          <h2 className="landing__heading">Why Work-Based Learning matters</h2>
          {WHY_WBL.map((item) => (
            <p key={item.title} className="landing__point">
              <strong>{item.title}.</strong> {item.text}
            </p>
          ))}
        </section>

        <aside className="landing__requirements" aria-labelledby="requirements-title">
          <h2 id="requirements-title" className="landing__heading">Key requirements</h2>
          <WblRequirements />
        </aside>
      </main>

      <footer className="landing__footer">
        <div className="landing__container">
          Strathmore University, School of Computing and Engineering Sciences
        </div>
      </footer>
    </div>
  );
}
