/**
 * Editable list of required units for an opportunity (2 to 5 rows).
 *
 * Each row: unit dropdown (units already chosen in other rows are disabled),
 * an Essential/Desirable toggle, and an optional minimum mark.
 * API errors arrive keyed as "requirements.<index>.<field>" and are shown on that row.
 *
 * This component doesn't keep its own copy of the rows. The parent (OpportunityForm)
 * owns them, and every change is reported back through onChange(newRows). That keeps
 * one single source of truth for the data.
 */
export const MIN_ROWS = 2;
export const MAX_ROWS = 5;

let nextKey = 1;   // counter for unique row ids (lives outside the component, so it keeps counting)

/** A new requirement row. Pass values to pre-fill it (used when editing). */
export function newRow(values = {}) {
  // `key` is a client-only id so React keeps row state stable when rows are removed.
  return { key: nextKey++, unit_id: '', importance: 'essential', min_mark: '', ...values };
}

export default function RequirementsEditor({ rows, units, errors, onChange }) {
  // The units already picked in some row, e.g. {"4", "9"}. `.filter(Boolean)` drops empty "".
  const chosen = new Set(rows.map((r) => String(r.unit_id)).filter(Boolean));

  // Each helper builds a NEW array (never edits the old one) and hands it to the parent.
  // React only notices changes when it gets a new array/object.
  const updateRow = (index, patch) =>
    onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));  // change one row
  const removeRow = (index) => onChange(rows.filter((_, i) => i !== index));     // drop one row
  const addRow = () => onChange([...rows, newRow()]);                            // append a blank row

  return (
    <fieldset className="requirements">
      <legend>Requirements</legend>
      <p className="muted small">
        Choose {MIN_ROWS} to {MAX_ROWS} units. At least one must be <strong>essential</strong>.
        Essential units count twice as much as desirable ones when matching students.
      </p>
      {/* List-level errors, e.g. "must have between 2 and 5" or "at least one essential". */}
      {errors.requirements && <div className="alert alert--error">{errors.requirements}</div>}

      {rows.map((row, i) => {
        // Look up this row's error for a field, e.g. err('unit_id') → errors["requirements.0.unit_id"].
        const err = (field) => errors[`requirements.${i}.${field}`];
        return (
          <div className="req-row" key={row.key}>
            {/* --- Unit dropdown --- */}
            <div className={`field req-row__unit ${err('unit_id') ? 'field--invalid' : ''}`}>
              <label htmlFor={`req-unit-${row.key}`}>Unit</label>
              <select
                id={`req-unit-${row.key}`}
                value={row.unit_id}
                onChange={(e) => updateRow(i, { unit_id: e.target.value })}
              >
                <option value="">Select a unit…</option>
                {units.map((u) => (
                  <option
                    key={u.unit_id}
                    value={u.unit_id}
                    // Already picked in another row → disabled (but keep this row's own choice enabled).
                    disabled={chosen.has(String(u.unit_id)) && String(row.unit_id) !== String(u.unit_id)}
                  >
                    {u.unit_name}
                  </option>
                ))}
              </select>
              {err('unit_id') && <p className="field__error">{err('unit_id')}</p>}
            </div>

            {/* --- Essential / Desirable toggle (two buttons acting like radio buttons) --- */}
            <div className="field req-row__importance">
              <span className="label">Importance</span>
              <div className="segmented" role="radiogroup" aria-label="Importance">
                {['essential', 'desirable'].map((level) => (
                  <button
                    type="button"   // type="button" so clicking doesn't submit the form
                    key={level}
                    role="radio"
                    aria-checked={row.importance === level}
                    className={row.importance === level ? 'active' : ''}
                    onClick={() => updateRow(i, { importance: level })}
                  >
                    {level === 'essential' ? 'Essential' : 'Desirable'}
                  </button>
                ))}
              </div>
              {err('importance') && <p className="field__error">{err('importance')}</p>}
            </div>

            {/* --- Optional minimum mark --- */}
            <div className={`field req-row__min ${err('min_mark') ? 'field--invalid' : ''}`}>
              <label htmlFor={`req-min-${row.key}`}>Min mark</label>
              <input
                id={`req-min-${row.key}`}
                type="number"
                min="0"
                max="100"
                placeholder="Optional"
                value={row.min_mark}
                onChange={(e) => updateRow(i, { min_mark: e.target.value })}
              />
              {err('min_mark') && <p className="field__error">{err('min_mark')}</p>}
            </div>

            {/* --- Remove button (disabled at the minimum of 2 rows) --- */}
            <button
              type="button"
              className="btn btn--icon"
              onClick={() => removeRow(i)}
              disabled={rows.length <= MIN_ROWS}
              aria-label="Remove requirement"
              title={rows.length <= MIN_ROWS ? `At least ${MIN_ROWS} requirements are needed` : 'Remove'}
            >
              ✕
            </button>
          </div>
        );
      })}

      {/* Disabled at the maximum of 5 rows. */}
      <button type="button" className="btn btn--secondary" onClick={addRow} disabled={rows.length >= MAX_ROWS}>
        + Add requirement {rows.length >= MAX_ROWS && `(max ${MAX_ROWS})`}
      </button>
    </fieldset>
  );
}
