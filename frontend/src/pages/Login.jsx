import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { parseApiError } from '../api/client.js';
import FormField from '../components/FormField.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { dashboardPathFor } from '../utils/roles.js';

export default function Login() {
  const { login, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  // Success message passed by the Register page after sign-up.
  const successMessage = location.state?.message;

  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to={dashboardPathFor(user.role)} replace />;

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: undefined });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);
    try {
      const loggedIn = await login(form.email, form.password);
      navigate(dashboardPathFor(loggedIn.role), { replace: true });
    } catch (err) {
      const { message, fields } = parseApiError(err);
      setErrors(fields);
      setFormError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card" onSubmit={handleSubmit} noValidate>
        <h1>Sign in</h1>
        <p className="muted">Strathmore WBL Placement System</p>

        {successMessage && <div className="alert alert--success">{successMessage}</div>}
        {formError && <div className="alert alert--error">{formError}</div>}

        <FormField label="Email" name="email" type="email" autoComplete="email"
          value={form.email} onChange={handleChange} error={errors.email} />
        <FormField label="Password" name="password" type="password" autoComplete="current-password"
          value={form.password} onChange={handleChange} error={errors.password} />

        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="switch-link">
          No account? <Link to="/register">Create one</Link>
        </p>
      </form>
    </div>
  );
}
