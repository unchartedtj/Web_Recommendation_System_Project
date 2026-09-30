import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { register } from '../api/auth.js';
import { parseApiError } from '../api/client.js';
import FormField from '../components/FormField.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { ROLES, dashboardPathFor } from '../utils/roles.js';

// Field definitions per role. The toggle swaps which set is rendered and submitted.
const COMMON_FIELDS = [
  { name: 'email', label: 'Email', type: 'email', autoComplete: 'email' },
  { name: 'password', label: 'Password', type: 'password', autoComplete: 'new-password',
    placeholder: 'At least 8 characters, with a letter and a number' },
  { name: 'confirm_password', label: 'Confirm password', type: 'password', autoComplete: 'new-password' },
];
const ROLE_FIELDS = {
  [ROLES.STUDENT]: [
    { name: 'admission_no', label: 'Admission number', inputMode: 'numeric' },
    { name: 'first_name', label: 'First name', autoComplete: 'given-name' },
    { name: 'last_name', label: 'Last name', autoComplete: 'family-name' },
    { name: 'course', label: 'Course', placeholder: 'e.g. BSc Informatics and Computer Science' },
    { name: 'year_of_study', label: 'Year of study', type: 'number', min: 1, max: 4 },
  ],
  [ROLES.PARTNER]: [
    { name: 'organization_name', label: 'Organization name', autoComplete: 'organization' },
    { name: 'contact_person', label: 'Contact person', autoComplete: 'name' },
    { name: 'phone', label: 'Phone', type: 'tel', autoComplete: 'tel', placeholder: '+254 7XX XXX XXX' },
  ],
};

export default function Register() {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  const [role, setRole] = useState(ROLES.STUDENT);
  // One shared values object, so switching roles doesn't wipe email/password.
  const [values, setValues] = useState({});
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) return <Navigate to={dashboardPathFor(user.role)} replace />;

  const fields = [...COMMON_FIELDS, ...ROLE_FIELDS[role]];

  const handleChange = (e) => {
    setValues({ ...values, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: undefined }); // clear the error once the user edits
  };

  const switchRole = (next) => {
    setRole(next);
    setErrors({});
    setFormError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);
    // Only send fields that belong to the selected role.
    const payload = { role };
    fields.forEach((f) => { payload[f.name] = values[f.name] ?? ''; });
    try {
      await register(payload);
      navigate('/login', {
        replace: true,
        state: { message: 'Registration successful. Please sign in.' },
      });
    } catch (err) {
      const { message, fields: fieldErrors } = parseApiError(err);
      setErrors(fieldErrors);
      setFormError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card card--wide" onSubmit={handleSubmit} noValidate>
        <h1>Create an account</h1>

        <div className="role-toggle" role="tablist" aria-label="Account type">
          <button type="button" role="tab" aria-selected={role === ROLES.STUDENT}
            className={role === ROLES.STUDENT ? 'active' : ''}
            onClick={() => switchRole(ROLES.STUDENT)}>
            Student
          </button>
          <button type="button" role="tab" aria-selected={role === ROLES.PARTNER}
            className={role === ROLES.PARTNER ? 'active' : ''}
            onClick={() => switchRole(ROLES.PARTNER)}>
            Industry Partner
          </button>
        </div>

        {formError && <div className="alert alert--error">{formError}</div>}

        <div className="form-grid">
          {fields.map(({ name, label, ...rest }) => (
            <FormField key={name} name={name} label={label} {...rest}
              value={values[name] ?? ''} onChange={handleChange} error={errors[name]} />
          ))}
        </div>

        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Register'}
        </button>
        <p className="switch-link">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
