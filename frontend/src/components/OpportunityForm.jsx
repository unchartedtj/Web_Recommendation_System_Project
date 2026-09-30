import { useState } from 'react';
import FormField from './FormField.jsx';
import RequirementsEditor, { newRow } from './RequirementsEditor.jsx';

const EMPTY_DETAILS = {
  title: '',
  description: '',
  sector: '',
  location: '',
  duration_months: '3',
  slots: '1',
  application_deadline: '',
};

function tomorrowISO() {
  // Local date, not toISOString(), which is UTC and can be a day off in Nairobi (UTC+3).
  const d = new Date();
  d.setDate(d.getDate() + 1);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Convert an API opportunity into form state (used when editing). */
export function toFormState(opportunity) {
  return {
    details: {
      title: opportunity.title ?? '',
      description: opportunity.description ?? '',
      sector: opportunity.sector ?? '',
      location: opportunity.location ?? '',
      duration_months: String(opportunity.duration_months ?? ''),
      slots: String(opportunity.slots ?? ''),
      application_deadline: opportunity.application_deadline ?? '',
    },
    requirements: opportunity.requirements.map((r) =>
      newRow({ unit_id: String(r.unit_id), importance: r.importance, min_mark: r.min_mark ?? '' }),
    ),
  };
}

/**
 * Shared create/edit form for an opportunity and its requirements.
 * `onSubmit(payload)` should throw the parsed API error ({message, fields}) on failure.
 */
export default function OpportunityForm({ units, initial, submitLabel, onSubmit, onCancel }) {
  const [details, setDetails] = useState(initial?.details ?? EMPTY_DETAILS);
  const [rows, setRows] = useState(initial?.requirements ?? [newRow(), newRow()]);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleDetail = (e) => {
    setDetails({ ...details, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: undefined });
  };

  const handleRows = (next) => {
    setRows(next);
    // Row indices may have shifted, so clear all requirement errors rather than show them on the wrong row.
    setErrors(Object.fromEntries(Object.entries(errors).filter(([k]) => !k.startsWith('requirements'))));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);
    const payload = {
      ...details,
      duration_months: details.duration_months === '' ? null : Number(details.duration_months),
      slots: details.slots === '' ? null : Number(details.slots),
      requirements: rows.map((r) => ({
        unit_id: r.unit_id === '' ? null : Number(r.unit_id),
        importance: r.importance,
        min_mark: r.min_mark === '' ? null : Number(r.min_mark),
      })),
    };
    try {
      await onSubmit(payload);
    } catch ({ message, fields }) {
      setErrors(fields || {});
      setFormError(message);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setSubmitting(false);
    }
  };

  const field = (name, label, props = {}) => (
    <FormField name={name} label={label} value={details[name]} onChange={handleDetail}
      error={errors[name]} {...props} />
  );

  return (
    <form className="panel" onSubmit={handleSubmit} noValidate>
      {formError && <div className="alert alert--error">{formError}</div>}

      <div className="form-grid">
        {field('title', 'Title', { className: 'span-2', placeholder: 'e.g. Software Development Intern' })}
        {field('description', 'Description', { as: 'textarea', rows: 4, className: 'span-2' })}
        {field('sector', 'Sector', { placeholder: 'e.g. Software Engineering' })}
        {field('location', 'Location', { placeholder: 'e.g. Nairobi' })}
        {field('duration_months', 'Duration (months)', { type: 'number', min: 1, max: 12 })}
        {field('slots', 'Slots available', { type: 'number', min: 1 })}
        {field('application_deadline', 'Application deadline', { type: 'date', min: tomorrowISO() })}
      </div>

      <RequirementsEditor rows={rows} units={units} errors={errors} onChange={handleRows} />

      <div className="form-actions">
        {onCancel && (
          <button type="button" className="btn btn--secondary" onClick={onCancel}>Cancel</button>
        )}
        <button type="submit" className="btn btn--primary" disabled={submitting}>
          {submitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
