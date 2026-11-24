/**
 * "My Profile" (/student/profile): a 4-step form the student fills in once and can edit later.
 *   1. Grades     – a mark for each of the 12 units, with the letter grade shown live
 *   2. Skills     – up to 10 technical skills, picked as chips grouped by category
 *   3. Interests  – 1 to 3 career sectors, picked as cards
 *   4. Summary    – review, then "Save & get recommendations"
 *
 * Saving sends everything in ONE request (PUT /api/student/profile). The server checks it
 * again, generates recommendations, and we go to /student/recommendations.
 * A 409 reply means "all marks are identical": we ask the student to confirm and resend.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchSectors, fetchSkillCategories, fetchUnits } from '../../api/catalog.js';
import { parseApiError } from '../../api/client.js';
import { fetchProfile, saveProfile } from '../../api/student.js';
import StudentLayout from '../../components/student/StudentLayout.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import { letterGrade } from '../../utils/grades.js';

const STEPS = ['Grades', 'Skills', 'Career interests', 'Summary'];
const MAX_SKILLS = 10;
const MAX_INTERESTS = 3;

/** Problems on the Grades step (checked before moving on), keyed like the server: grades.<id>. */
function gradeProblems(units, grades) {
  const problems = {};
  for (const u of units) {
    const raw = grades[u.unit_id];
    if (raw === undefined || raw === '') problems[`grades.${u.unit_id}`] = 'Enter a mark';
    else if (Number.isNaN(Number(raw)) || Number(raw) < 0 || Number(raw) > 100) {
      problems[`grades.${u.unit_id}`] = 'Mark must be between 0 and 100';
    } else if (!/^\d+(\.\d{1,2})?$/.test(String(raw).trim())) {
      problems[`grades.${u.unit_id}`] = 'At most 2 decimal places';
    }
  }
  return problems;
}

/** Which step a server error belongs to, so we can jump back to it. */
function stepForError(field) {
  if (field.startsWith('grades')) return 0;
  if (field === 'skill_ids') return 1;
  if (field === 'sector_ids') return 2;
  return 3;
}

export default function StudentProfile() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  // Data from the server
  const [units, setUnits] = useState(null);
  const [categories, setCategories] = useState(null);
  const [sectors, setSectors] = useState(null);
  // What the student has entered (pre-filled from their last save)
  const [grades, setGrades] = useState({});           // { unit_id: "72.5" } (text from the inputs)
  const [skillIds, setSkillIds] = useState([]);
  const [sectorIds, setSectorIds] = useState([]);
  // Messages
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [saving, setSaving] = useState(false);

  // Load the lists and the student's current profile when the page opens.
  useEffect(() => {
    Promise.all([fetchUnits(), fetchSkillCategories(), fetchSectors(), fetchProfile()])
      .then(([u, c, s, profile]) => {
        setUnits(u);
        setCategories(c);
        setSectors(s);
        setGrades(Object.fromEntries(Object.entries(profile.grades).map(([k, v]) => [k, String(v)])));
        setSkillIds(profile.skill_ids);
        setSectorIds(profile.sector_ids);
      })
      .catch((err) => setLoadError(parseApiError(err).message));
  }, []);

  const ready = units && categories && sectors;

  // ---- helpers to change the selections ----
  const setMark = (unitId, value) => {
    setGrades({ ...grades, [unitId]: value });
    setErrors({ ...errors, [`grades.${unitId}`]: undefined, grades: undefined });
  };
  const toggle = (list, setList, id, max, errorKey) => {
    setErrors({ ...errors, [errorKey]: undefined });
    if (list.includes(id)) setList(list.filter((x) => x !== id));
    else if (list.length < max) setList([...list, id]);
  };

  // ---- step navigation (each step is checked before moving forward) ----
  const next = () => {
    setFormError('');
    if (step === 0) {
      const problems = gradeProblems(units, grades);
      if (Object.keys(problems).length) {
        setErrors(problems);
        setFormError('Please enter a valid mark (0 to 100) for every unit.');
        return;
      }
    }
    if (step === 1 && skillIds.length === 0) {
      setErrors({ skill_ids: `Choose between 1 and ${MAX_SKILLS} skills` });
      return;
    }
    if (step === 2 && sectorIds.length === 0) {
      setErrors({ sector_ids: `Choose between 1 and ${MAX_INTERESTS} career interests` });
      return;
    }
    setStep(step + 1);
  };
  const back = () => { setFormError(''); setStep(step - 1); };

  // ---- save ----
  const save = async (confirmImplausible = false) => {
    setSaving(true);
    setFormError('');
    const payload = {
      grades: Object.fromEntries(Object.entries(grades).map(([k, v]) => [k, Number(v)])),
      skill_ids: skillIds,
      sector_ids: sectorIds,
      ...(confirmImplausible ? { confirm_implausible: true } : {}),
    };
    try {
      await saveProfile(payload);
      navigate('/student/recommendations', {
        state: { message: 'Profile saved. Here are your recommendations.' },
      });
    } catch (err) {
      const { message, fields } = parseApiError(err);
      if (err.response?.status === 409) {
        // "Implausible entry": all marks identical. Ask, and resend with confirmation.
        setSaving(false);
        if (window.confirm(`${message}\n\nSave anyway?`)) save(true);
        return;
      }
      setErrors(fields);
      setFormError(message);
      // Jump back to the first step that has a problem.
      const steps = Object.keys(fields).map(stepForError);
      if (steps.length) setStep(Math.min(...steps));
    }
    setSaving(false);
  };

  // ---- small lookups for the summary ----
  const skillName = Object.fromEntries((categories ?? []).flatMap((c) => c.skills.map((s) => [s.skill_id, s.name])));
  const sectorName = Object.fromEntries((sectors ?? []).map((s) => [s.sector_id, s.name]));
  const marks = Object.values(grades).filter((v) => v !== '').map(Number);
  const average = marks.length ? (marks.reduce((a, b) => a + b, 0) / marks.length).toFixed(1) : '—';

  return (
    <StudentLayout>
      <h1>My profile</h1>
      <ErrorBanner message={loadError} onRetry={() => window.location.reload()} />
      {!ready && !loadError && <LoadingSkeleton variant="cards" count={1} />}

      {ready && (
        <div className="panel">
          {/* ---- The stepper: shows where you are ---- */}
          <ol className="stepper">
            {STEPS.map((label, i) => (
              <li key={label} className={i === step ? 'active' : i < step ? 'done' : ''}>
                <span className="stepper__num">{i < step ? '✓' : i + 1}</span>
                <span className="stepper__label">{label}</span>
              </li>
            ))}
          </ol>

          {formError && <div className="alert alert--error">{formError}</div>}

          {/* ---- Step 1: Grades ---- */}
          {step === 0 && (
            <div>
              <p className="muted">Enter your mark out of 100 for each unit. The letter grade uses
                Strathmore's scale (A 70+, B 60–69, C 50–59, D 40–49, E below 40).</p>
              {errors.grades && <div className="alert alert--error">{errors.grades}</div>}
              <div className="grades-grid">
                {units.map((u) => {
                  const err = errors[`grades.${u.unit_id}`];
                  const letter = letterGrade(grades[u.unit_id]);
                  return (
                    <div key={u.unit_id} className={`grade-row ${err ? 'field--invalid' : ''}`}>
                      <label htmlFor={`mark-${u.unit_id}`}>{u.unit_name}</label>
                      <input id={`mark-${u.unit_id}`} type="number" min="0" max="100" step="0.01"
                        inputMode="decimal" value={grades[u.unit_id] ?? ''}
                        onChange={(e) => setMark(u.unit_id, e.target.value)} />
                      <span className={`grade-letter grade-letter--${letter || 'none'}`}>{letter || '–'}</span>
                      {err && <p className="field__error">{err}</p>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ---- Step 2: Skills ---- */}
          {step === 1 && (
            <div>
              <p className="muted">Pick the technical skills you have.{' '}
                <strong>{skillIds.length}/{MAX_SKILLS} selected</strong></p>
              {errors.skill_ids && <div className="alert alert--error">{errors.skill_ids}</div>}
              {categories.map((c) => (
                <div key={c.category} className="skill-group">
                  <p className="skill-group__title">{c.category}</p>
                  <div className="chips">
                    {c.skills.map((s) => {
                      const on = skillIds.includes(s.skill_id);
                      return (
                        <button type="button" key={s.skill_id}
                          className={`chip chip--button ${on ? 'chip--selected' : ''}`}
                          aria-pressed={on}
                          disabled={!on && skillIds.length >= MAX_SKILLS}
                          onClick={() => toggle(skillIds, setSkillIds, s.skill_id, MAX_SKILLS, 'skill_ids')}>
                          {on ? '✓ ' : ''}{s.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ---- Step 3: Career interests ---- */}
          {step === 2 && (
            <div>
              <p className="muted">Pick 1 to {MAX_INTERESTS} areas you'd like to work in.{' '}
                <strong>{sectorIds.length}/{MAX_INTERESTS} selected</strong></p>
              {errors.sector_ids && <div className="alert alert--error">{errors.sector_ids}</div>}
              <div className="interest-cards">
                {sectors.map((s) => {
                  const on = sectorIds.includes(s.sector_id);
                  return (
                    <button type="button" key={s.sector_id}
                      className={`interest-card ${on ? 'interest-card--selected' : ''}`}
                      aria-pressed={on}
                      disabled={!on && sectorIds.length >= MAX_INTERESTS}
                      onClick={() => toggle(sectorIds, setSectorIds, s.sector_id, MAX_INTERESTS, 'sector_ids')}>
                      <span className="interest-card__check">{on ? '✓' : ''}</span>
                      {s.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* ---- Step 4: Summary ---- */}
          {step === 3 && (
            <div className="summary">
              <h3>Grades</h3>
              <p>{units.length} units entered · average mark <strong>{average}</strong></p>
              <h3>Skills ({skillIds.length})</h3>
              <div className="chips">
                {skillIds.map((id) => <span key={id} className="chip">{skillName[id]}</span>)}
              </div>
              <h3>Career interests ({sectorIds.length})</h3>
              <div className="chips">
                {sectorIds.map((id) => <span key={id} className="chip chip--essential">{sectorName[id]}</span>)}
              </div>
            </div>
          )}

          {/* ---- Back / Next / Save ---- */}
          <div className="form-actions">
            {step > 0 && <button type="button" className="btn btn--secondary" onClick={back}>Back</button>}
            {step < STEPS.length - 1 && (
              <button type="button" className="btn btn--primary" onClick={next}>Next</button>
            )}
            {step === STEPS.length - 1 && (
              <button type="button" className="btn btn--primary" disabled={saving} onClick={() => save()}>
                {saving ? 'Saving…' : 'Save & get recommendations'}
              </button>
            )}
          </div>
        </div>
      )}
    </StudentLayout>
  );
}
