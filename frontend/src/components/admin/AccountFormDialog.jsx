/**
 * Add / edit a student or an industry partner (admin). The same fields as the sign-up form;
 * a password is only asked for when creating. Field errors from the API appear under each box.
 *
 *   kind     'student' | 'partner'
 *   initial  the current values when editing (no password fields then)
 *   onSave   async (values) => ...; throw the parsed API error ({message, fields}) on failure
 */
import { useState } from 'react';
import FormField from '../FormField.jsx';
import ConfirmDialog from '../ui/ConfirmDialog.jsx';

const FIELDS = {
  student: [
    { name: 'first_name', label: 'First name' },
    { name: 'last_name', label: 'Last name' },
    { name: 'email', label: 'Email', type: 'email', placeholder: 'name@strathmore.edu' },
    { name: 'admission_no', label: 'Admission number', inputMode: 'numeric' },
    { name: 'course', label: 'Course', placeholder: 'e.g. BBIT' },
  ],
  partner: [
    { name: 'organization_name', label: 'Organisation' },
    { name: 'contact_person', label: 'Contact person' },
    { name: 'email', label: 'Email', type: 'email' },
    { name: 'phone', label: 'Phone', placeholder: 'e.g. 0712 345 678' },
  ],
};

export default function AccountFormDialog({ kind, initial, onSave, onCancel }) {
  const creating = !initial;
  const [values, setValues] = useState(() => ({
    ...(kind === 'student' ? { year_of_study: '3' } : {}),
    ...(initial ?? {}),
    ...(initial?.year_of_study ? { year_of_study: String(initial.year_of_study) } : {}),
    password: '', confirm_password: '',
  }));
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const noun = kind === 'student' ? 'student' : 'partner';

  const change = (e) => {
    setValues({ ...values, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: undefined });
  };

  const save = async () => {
    setBusy(true);
    setError('');
    const body = { ...values };
    if (kind === 'student') body.year_of_study = Number(values.year_of_study);
    if (!creating) { delete body.password; delete body.confirm_password; }
    try {
      await onSave(body);
    } catch ({ message, fields }) {
      setErrors(fields ?? {});
      setError(message);
      setBusy(false);
    }
  };

  return (
    <ConfirmDialog title={creating ? `Add ${noun}` : `Edit ${noun}`} busy={busy} error={error}
      confirmLabel={creating ? `Create ${noun}` : 'Save changes'} onConfirm={save} onCancel={onCancel}>
      <div className="dialog-form">
        {FIELDS[kind].map(({ name, ...rest }) => (
          <FormField key={name} name={`acc-${name}`} {...rest} value={values[name] ?? ''} error={errors[name]}
            onChange={(e) => change({ target: { name, value: e.target.value } })} />
        ))}
        {kind === 'student' && (
          <div className={`field ${errors.year_of_study ? 'field--invalid' : ''}`}>
            <label htmlFor="acc-year">Year of study</label>
            <select id="acc-year" value={values.year_of_study} onChange={(e) => change({ target: { name: 'year_of_study', value: e.target.value } })}>
              {[1, 2, 3, 4].map((y) => <option key={y} value={y}>Year {y}</option>)}
            </select>
            {errors.year_of_study && <p className="field__error">{errors.year_of_study}</p>}
          </div>
        )}
        {creating && (
          <>
            <FormField name="acc-password" label="Password" type="password" autoComplete="new-password"
              placeholder="At least 8 characters, with a letter and a number"
              value={values.password} error={errors.password}
              onChange={(e) => change({ target: { name: 'password', value: e.target.value } })} />
            <FormField name="acc-confirm" label="Confirm password" type="password" autoComplete="new-password"
              value={values.confirm_password} error={errors.confirm_password}
              onChange={(e) => change({ target: { name: 'confirm_password', value: e.target.value } })} />
          </>
        )}
      </div>
    </ConfirmDialog>
  );
}
