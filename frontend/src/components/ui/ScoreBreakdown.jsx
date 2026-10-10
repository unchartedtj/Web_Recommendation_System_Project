/**
 * The three parts of the match score as small bars:
 *   Grades (60%) · Skills (25%) · Interests (15%)
 * Each bar shows that part's own score (0–100%); the label shows its weight in the total.
 * The weights match the backend config MATCH_WEIGHTS.
 */
const PARTS = [
  { key: 'grade_score', label: 'Grades', weight: 60 },
  { key: 'skill_score', label: 'Skills', weight: 25 },
  { key: 'interest_score', label: 'Interests', weight: 15 },
];

export default function ScoreBreakdown({ breakdown }) {
  return (
    <dl className="breakdown">
      {PARTS.map(({ key, label, weight }) => {
        const pct = Math.round((breakdown?.[key] ?? 0) * 100);
        return (
          <div key={key} className="breakdown__row">
            <dt>{label} <span className="muted">({weight}%)</span></dt>
            <dd>
              <span className="breakdown__track" role="progressbar" aria-label={`${label} score`}
                aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                <span className="breakdown__fill" style={{ width: `${pct}%` }} />
              </span>
              <span className="breakdown__value">{pct}%</span>
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
