/**
 * Login page (/login).
 *
 * React basics used here:
 * - useState(initial) gives [value, setValue]. Calling setValue(...) stores a new value
 *   AND re-draws the component, which is how the screen updates.
 * - A "controlled input" shows value={form.email} and updates state on every keystroke
 *   (onChange), so React state is always the single source of truth.
 */
import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { parseApiError } from '../api/client.js';
import FormField from '../components/FormField.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { dashboardPathFor } from '../utils/roles.js';

export default function Login() {
  const { login, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();     // function to change page from code
  const location = useLocation();     // info about the current URL (incl. data passed along)
  // Success message passed by the Register page after sign-up.
  // `?.` = "optional chaining": gives undefined instead of crashing if state is null.
  const successMessage = location.state?.message;

  const [form, setForm] = useState({ email: '', password: '' });   // what the user typed
  const [errors, setErrors] = useState({});                        // per-field errors from the API
  const [formError, setFormError] = useState('');                  // the red banner message
  const [submitting, setSubmitting] = useState(false);             // true while waiting for the server

  // Already logged in? Skip the login page and go straight to the dashboard.
  if (isAuthenticated) return <Navigate to={dashboardPathFor(user.role)} replace />;

  const handleChange = (e) => {
    // e.target is the input that changed; its name ("email"/"password") picks the field.
    // [e.target.name]: ... is a "computed key", so one handler works for every input.
    setForm({ ...form, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: undefined });   // hide that field's error while typing
  };

  const handleSubmit = async (e) => {
    e.preventDefault();       // stop the browser's default full-page form submit
    setFormError('');
    setSubmitting(true);
    try {
      // `await` waits for the server's reply before continuing.
      const loggedIn = await login(form.email, form.password);
      // Send each role to its own dashboard. replace: true means Back won't return to /login.
      navigate(dashboardPathFor(loggedIn.role), { replace: true });
    } catch (err) {
      // Wrong password etc.: show the API's message(s).
      const { message, fields } = parseApiError(err);
      setErrors(fields);
      setFormError(message);
    } finally {
      setSubmitting(false);   // runs whether it succeeded or failed
    }
  };

  // Everything below is JSX: HTML-like markup inside JavaScript.
  // className = HTML's "class"; {expression} inserts a JavaScript value.
  return (
    <div className="auth-page">
      {/* noValidate: turn off the browser's own pop-up checks; the server's messages are shown instead. */}
      <form className="card" onSubmit={handleSubmit} noValidate>
        <h1>Sign in</h1>
        <p className="muted">Strathmore WBL Placement System</p>

        {/* `a && <X/>` shows <X/> only when `a` is truthy. */}
        {successMessage && <div className="alert alert--success">{successMessage}</div>}
        {formError && <div className="alert alert--error">{formError}</div>}

        <FormField label="Email" name="email" type="email" autoComplete="email"
          value={form.email} onChange={handleChange} error={errors.email} />
        <FormField label="Password" name="password" type="password" autoComplete="current-password"
          value={form.password} onChange={handleChange} error={errors.password} />

        {/* Disabled while submitting, so a double-click can't send two requests. */}
        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="switch-link">
          {/* <Link> changes page without reloading the whole site (unlike a plain <a>). */}
          No account? <Link to="/register">Create one</Link>
        </p>
      </form>
    </div>
  );
}
