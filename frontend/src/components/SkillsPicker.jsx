/**
 * "Required Skills" section of the Post/Edit Opportunity form (partners).
 *
 * - A search box filters the preset skills, which are shown grouped by category.
 * - Clicking a skill adds it as a row with an Essential/Desirable toggle and a remove button.
 * - At most 8 skills; at least one must be essential (the server checks this too).
 * API errors arrive as "skills" (whole list) or "skills.<index>.skill_id" (one row).
 *
 * Like RequirementsEditor, the parent owns the rows and receives every change via onChange.
 */
import { useState } from 'react';

export const MAX_SKILLS = 8;

let nextKey = 1;
/** A selected-skill row. `key` is a client-only id so React can track rows. */
export function newSkillRow(values = {}) {
  return { key: nextKey++, skill_id: '', importance: 'essential', ...values };
}

export default function SkillsPicker({ categories, rows, errors, onChange }) {
  const [search, setSearch] = useState('');
  const chosen = new Set(rows.map((r) => Number(r.skill_id)));
  const names = Object.fromEntries(
    categories.flatMap((c) => c.skills.map((s) => [s.skill_id, s.name])),
  );
  const atMax = rows.length >= MAX_SKILLS;

  // Keep only skills whose name (or category) contains the search text; drop empty groups.
  const term = search.trim().toLowerCase();
  const filtered = categories
    .map((c) => ({
      ...c,
      skills: c.skills.filter((s) => !term || s.name.toLowerCase().includes(term)
        || c.category.toLowerCase().includes(term)),
    }))
    .filter((c) => c.skills.length > 0);

  const add = (skillId) => onChange([...rows, newSkillRow({ skill_id: skillId })]);
  const update = (i, patch) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const remove = (i) => onChange(rows.filter((_, j) => j !== i));

  return (
    <fieldset className="requirements">
      <legend>Required Skills</legend>
      <p className="muted small">
        Pick 1 to {MAX_SKILLS} skills from the list. At least one must be <strong>essential</strong>.
        Students missing a skill are still shown the internship, with the gap listed.
      </p>
      {errors.skills && <div className="alert alert--error">{errors.skills}</div>}

      {/* --- The selected skills --- */}
      {rows.length === 0 && <p className="muted small">No skills selected yet.</p>}
      {rows.map((row, i) => {
        const err = errors[`skills.${i}.skill_id`] || errors[`skills.${i}.importance`];
        return (
          <div className="skill-row" key={row.key}>
            <span className="skill-row__name">{names[row.skill_id] ?? `Skill #${row.skill_id}`}</span>
            <div className="segmented" role="radiogroup" aria-label="Importance">
              {['essential', 'desirable'].map((level) => (
                <button
                  type="button"
                  key={level}
                  role="radio"
                  aria-checked={row.importance === level}
                  className={row.importance === level ? 'active' : ''}
                  onClick={() => update(i, { importance: level })}
                >
                  {level === 'essential' ? 'Essential' : 'Desirable'}
                </button>
              ))}
            </div>
            <button type="button" className="btn btn--icon" onClick={() => remove(i)}
              aria-label={`Remove ${names[row.skill_id]}`}>
              ✕
            </button>
            {err && <p className="field__error skill-row__error">{err}</p>}
          </div>
        );
      })}

      {/* --- Search + available skills --- */}
      <div className="field skill-search">
        <label htmlFor="skill-search">
          Add skills <span className="muted small">({rows.length}/{MAX_SKILLS})</span>
        </label>
        <input
          id="skill-search"
          type="search"
          placeholder="Search skills, e.g. Python or Data"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="skill-groups">
        {filtered.map((c) => (
          <div key={c.category} className="skill-group">
            <p className="skill-group__title">{c.category}</p>
            <div className="chips">
              {c.skills.map((s) => (
                <button
                  type="button"
                  key={s.skill_id}
                  className="chip chip--button"
                  // Already picked, or the 8-skill limit is reached → can't add.
                  disabled={chosen.has(s.skill_id) || atMax}
                  onClick={() => add(s.skill_id)}
                >
                  {chosen.has(s.skill_id) ? '✓ ' : '+ '}{s.name}
                </button>
              ))}
            </div>
          </div>
        ))}
        {filtered.length === 0 && <p className="muted small">No skills match "{search}".</p>}
      </div>
    </fieldset>
  );
}
