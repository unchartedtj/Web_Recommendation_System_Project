/**
 * Change password (/account/password), for every role.
 * Also the ONLY page a user can open after an admin reset their password: until they choose
 * a new one, every other page redirects here.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { changePassword } from '../api/account.js';
import { parseApiError } from '../api/client.js';
import FormField from '../components/FormField.jsx';
import RoleLayout from '../components/RoleLayout.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { dashboardPathFor } from '../utils/roles.js';

const EMPTY = { current_password: '', new_password: '', confirm_password: '' };

export default function ChangePassword() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const forced = Boolean(user?.must_change_password);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: undefined });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const fresh = await changePassword(form);
      updateUser(fresh);
      setForm(EMPTY);
      setErrors({});
      if (forced) {
        navigate(dashboardPathFor(fresh.role), { replace: true });
      } else {
        setMessage('Your password has been changed.');
      }
    } catch (err) {
      const { message: msg, fields } = parseApiError(err);
      setErrors(fields);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <RoleLayout title="Change password">
      <form className="panel narrow-form" onSubmit={handleSubmit} noValidate>
        {forced && (
          <div className="alert alert--warn" role="status">
            An administrator reset your password. Please choose a new password to continue.
          </div>
        )}
        {message && <div className="alert alert--success" role="status">{message}</div>}
        {error && <div className="alert alert--error" role="alert">{error}</div>}
        <FormField label={forced ? 'Temporary password' : 'Current password'} name="current_password"
          type="password" autoComplete="current-password" value={form.current_password}
          onChange={handleChange} error={errors.current_password} />
        <FormField label="New password" name="new_password" type="password" autoComplete="new-password"
          placeholder="At least 8 characters, with a letter and a number"
          value={form.new_password} onChange={handleChange} error={errors.new_password} />
        <FormField label="Confirm new password" name="confirm_password" type="password"
          autoComplete="new-password" value={form.confirm_password} onChange={handleChange}
          error={errors.confirm_password} />
        <button type="submit" className="btn btn--primary" disabled={saving}>
          {saving ? 'Saving…' : 'Change password'}
        </button>
      </form>
    </RoleLayout>
  );
}
