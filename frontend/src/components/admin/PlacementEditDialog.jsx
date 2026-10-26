/**
 * Edit a placement's status and dates. The status list only offers the allowed next steps:
 *   confirmed → ongoing → completed, and confirmed/ongoing → terminated (reason required).
 * Problems are shown BEFORE anything is sent: a missing reason for Terminated, a missing start
 * date for Ongoing/Completed, or an end date that isn't after the start date.
 */
import { useState } from 'react';
import ConfirmDialog from '../ui/ConfirmDialog.jsx';
import { PLACEMENT_LABELS } from './Pill.jsx';

export function validatePlacementEdit({ status, start_date, end_date, reason }) {
  const errors = {};
  if (status === 'terminated' && !reason.trim()) {
    errors.reason = 'A reason is required to terminate a placement';
  }
  if ((status === 'ongoing' || status === 'completed') && !start_date) {
    errors.start_date = 'A start date is required once the placement is ongoing';
  }
  if (start_date && end_date && end_date <= start_date) {
    errors.end_date = 'The end date must be after the start date';
  }
  return errors;
}

export default function PlacementEditDialog({ placement, onSave, onCancel }) {
  const [form, setForm] = useState({
    status: placement.status,
    start_date: placement.start_date ?? '',
    end_date: placement.end_date ?? '',
    reason: '',
  });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [busy, setBusy] = useState(false);
  const options = [placement.status, ...placement.allowed_next];

  const set = (field) => (e) => {
    setForm({ ...form, [field]: e.target.value });
    setErrors({ ...errors, [field]: undefined });
  };

  const submit = async () => {
    const found = validatePlacementEdit(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    const body = { start_date: form.start_date || null, end_date: form.end_date || null };
    if (form.status !== placement.status) body.status = form.status;
    if (form.reason.trim()) body.reason = form.reason.trim();
    setBusy(true);
    setApiError('');
    try {
      await onSave(body);
    } catch (err) {
      setApiError(err.message || 'Could not save the placement');
      setBusy(false);
    }
  };

  return (
    <ConfirmDialog title={`Edit placement: ${placement.student.name}`} confirmLabel="Save changes"
      busy={busy} error={apiError} onConfirm={submit} onCancel={onCancel}>
      <p className="muted small">{placement.opportunity.title} · {placement.company.name}</p>
      <div className={`field ${errors.status ? 'field--invalid' : ''}`}>
        <label htmlFor="placement-status">Status</label>
        <select id="placement-status" value={form.status} onChange={set('status')}>
          {options.map((s) => <option key={s} value={s}>{PLACEMENT_LABELS[s] ?? s}</option>)}
        </select>
      </div>
      <div className={`field ${errors.start_date ? 'field--invalid' : ''}`}>
        <label htmlFor="placement-start">Start date</label>
        <input id="placement-start" type="date" value={form.start_date} onChange={set('start_date')}
          aria-invalid={Boolean(errors.start_date)} aria-describedby="placement-start-error" />
        {errors.start_date && <p className="field__error" id="placement-start-error">{errors.start_date}</p>}
      </div>
      <div className={`field ${errors.end_date ? 'field--invalid' : ''}`}>
        <label htmlFor="placement-end">End date</label>
        <input id="placement-end" type="date" value={form.end_date} onChange={set('end_date')}
          aria-invalid={Boolean(errors.end_date)} aria-describedby="placement-end-error" />
        {errors.end_date && <p className="field__error" id="placement-end-error">{errors.end_date}</p>}
      </div>
      <div className={`field ${errors.reason ? 'field--invalid' : ''}`}>
        <label htmlFor="placement-reason">
          Reason {form.status === 'terminated' ? '(required)' : '(optional)'}
        </label>
        <textarea id="placement-reason" rows={2} maxLength={255} value={form.reason}
          onChange={set('reason')} aria-invalid={Boolean(errors.reason)}
          aria-describedby="placement-reason-error" />
        {errors.reason && <p className="field__error" id="placement-reason-error">{errors.reason}</p>}
      </div>
    </ConfirmDialog>
  );
}
