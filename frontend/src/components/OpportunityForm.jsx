/**
 * The Post / Edit Opportunity form: details, a sector dropdown, the unit requirements
 * and the required skills.
 *
 * The same component is used for creating and editing. The parent page
 * (OpportunityEditor.jsx) decides what "submit" does and passes in any starting values.
 */
import { useState } from 'react';
import FormField from './FormField.jsx';
import RequirementsEditor, { newRow } from './RequirementsEditor.jsx';
import SkillsPicker, { newSkillRow } from './SkillsPicker.jsx';

// Starting values for a brand-new opportunity. Form inputs work with text,
// so numbers are strings here and converted back to numbers on submit.
const EMPTY_DETAILS = {
  title: '',
  description: '',
  sector_id: '',
  location: '',
  duration_months: '3',
  slots: '1',
  application_deadline: '',
};

/** Tomorrow's date as "YYYY-MM-DD", the earliest deadline the date picker allows. */
function tomorrowISO() {
  // Local date, not toISOString(), which is UTC and can be a day off in Nairobi (UTC+3).
  const d = new Date();
  d.setDate(d.getDate() + 1);
  const pad = (n) => String(n).padStart(2, '0');   // 5 → "05"
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;   // months start at 0
}

/** Convert an API opportunity into form state (used when editing). */
export function toFormState(opportunity) {
  return {
    details: {
      // `?? ''` → use an empty string if the value is null/undefined.
      title: opportunity.title ?? '',
      description: opportunity.description ?? '',
      sector_id: String(opportunity.sector_id ?? ''),
      location: opportunity.location ?? '',
      duration_months: String(opportunity.duration_months ?? ''),
      slots: String(opportunity.slots ?? ''),
      application_deadline: opportunity.application_deadline ?? '',
    },
    // Each saved requirement / skill becomes one editable row.
    requirements: opportunity.requirements.map((r) =>
      newRow({ unit_id: String(r.unit_id), importance: r.importance, min_mark: r.min_mark ?? '' }),
    ),
    skills: (opportunity.skills ?? []).map((s) =>
      newSkillRow({ skill_id: s.skill_id, importance: s.importance }),
    ),
  };
}

/**
 * Shared create/edit form for an opportunity, its requirements and required skills.
 * `onSubmit(payload)` should throw the parsed API error ({message, fields}) on failure.
 *
 * Props (inputs from the parent):
 *   units           – the unit catalogue for the requirement dropdowns
 *   sectors         – the preset sectors for the Sector dropdown
 *   counties        – Kenya's 47 counties for the Location dropdown
 *   skillCategories – the preset skills, grouped by category
 *   initial         – starting values when editing (undefined for a new opportunity)
 *   submitLabel     – button text, e.g. "Post opportunity" or "Save changes"
 *   onSubmit        – what to do with the data (create or update)
 *   onCancel        – what the Cancel button does
 */
export default function OpportunityForm({ units, sectors, counties = [], skillCategories, initial, submitLabel,
  onSubmit, onCancel }) {
  const [details, setDetails] = useState(initial?.details ?? EMPTY_DETAILS);
  // A new opportunity starts with 2 empty unit rows (the minimum allowed) and no skills.
  const [rows, setRows] = useState(initial?.requirements ?? [newRow(), newRow()]);
  const [skillRows, setSkillRows] = useState(initial?.skills ?? []);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Called on every change to a details field (text boxes and the sector dropdown).
  const handleDetail = (e) => {
    setDetails({ ...details, [e.target.name]: e.target.value });
    setErrors({ ...errors, [e.target.name]: undefined });
  };

  // Row indices may shift when rows are added/removed, so clear that list's errors rather
  // than show them on the wrong row.
  const withoutErrorsStartingWith = (prefix) =>
    Object.fromEntries(Object.entries(errors).filter(([k]) => !k.startsWith(prefix)));

  const handleRows = (next) => {
    setRows(next);
    setErrors(withoutErrorsStartingWith('requirements'));
  };

  const handleSkillRows = (next) => {
    setSkillRows(next);
    setErrors(withoutErrorsStartingWith('skills'));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setSubmitting(true);
    // Build the JSON the API expects: numbers as numbers, empty boxes as null.
    const payload = {
      ...details,
      sector_id: details.sector_id === '' ? null : Number(details.sector_id),
      duration_months: details.duration_months === '' ? null : Number(details.duration_months),
      slots: details.slots === '' ? null : Number(details.slots),
      requirements: rows.map((r) => ({
        unit_id: r.unit_id === '' ? null : Number(r.unit_id),
        importance: r.importance,
        min_mark: r.min_mark === '' ? null : Number(r.min_mark),
      })),
      skills: skillRows.map((s) => ({ skill_id: Number(s.skill_id), importance: s.importance })),
    };
    try {
      await onSubmit(payload);
    } catch ({ message, fields }) {
      // The parent re-throws the parsed API error; `{ message, fields }` unpacks it.
      setErrors(fields || {});
      setFormError(message);
      window.scrollTo({ top: 0, behavior: 'smooth' });   // so the error banner is visible
    } finally {
      setSubmitting(false);
    }
  };

  // Small helper so each details field is one short line below.
  const field = (name, label, props = {}) => (
    <FormField name={name} label={label} value={details[name]} onChange={handleDetail}
      error={errors[name]} {...props} />
  );

  return (
    <form className="panel" onSubmit={handleSubmit} noValidate>
      {formError && <div className="alert alert--error">{formError}</div>}

      {/* Details: a 2-column grid on wide screens (span-2 = full width). */}
      <div className="form-grid">
        {field('title', 'Title', { className: 'span-2', placeholder: 'e.g. Software Development Intern' })}
        {field('description', 'Description', { as: 'textarea', rows: 4, className: 'span-2' })}

        {/* Sector: chosen from the preset list (also used to match students' career interests). */}
        <div className={`field ${errors.sector_id ? 'field--invalid' : ''}`}>
          <label htmlFor="sector_id">Sector</label>
          <select id="sector_id" name="sector_id" value={details.sector_id} onChange={handleDetail}>
            <option value="">Select a sector…</option>
            {sectors.map((s) => (
              <option key={s.sector_id} value={s.sector_id}>{s.name}</option>
            ))}
          </select>
          {errors.sector_id && <p className="field__error">{errors.sector_id}</p>}
        </div>

        {/* Location: one of Kenya's 47 counties. An older free-text location that isn't a
            county is still shown (so editing doesn't silently lose it) until another is chosen. */}
        <div className={`field ${errors.location ? 'field--invalid' : ''}`}>
          <label htmlFor="location">Location (county)</label>
          <select id="location" name="location" value={details.location} onChange={handleDetail}
            aria-invalid={Boolean(errors.location)} aria-describedby={errors.location ? 'location-error' : undefined}>
            <option value="">Select a county…</option>
            {details.location && !counties.includes(details.location) && (
              <option value={details.location}>{details.location} (not a county: please choose one)</option>
            )}
            {counties.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          {errors.location && <p className="field__error" id="location-error">{errors.location}</p>}
        </div>
        {field('duration_months', 'Duration (months)', { type: 'number', min: 1, max: 12 })}
        {field('slots', 'Slots available', { type: 'number', min: 1 })}
        {/* min={tomorrow} stops the date picker offering past dates. */}
        {field('application_deadline', 'Application deadline', { type: 'date', min: tomorrowISO() })}
      </div>

      {/* The unit requirement rows (see RequirementsEditor.jsx). */}
      <RequirementsEditor rows={rows} units={units} errors={errors} onChange={handleRows} />

      {/* The required skills (see SkillsPicker.jsx). */}
      <SkillsPicker categories={skillCategories} rows={skillRows} errors={errors}
        onChange={handleSkillRows} />

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
