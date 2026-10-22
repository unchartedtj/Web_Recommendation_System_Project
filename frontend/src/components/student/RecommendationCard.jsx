/**
 * One recommendation on the Recommendations page.
 *
 * Shows: rank, title, company, sector, location, deadline, a large match %, the score
 * breakdown, the eligibility badge, an "Interest match" tag, and (for #1) a "Top match" ribbon.
 * "Why this match?" expands the unit table, the skill chips and a plain-English summary.
 * `from` is the current page URL, so the details page's Back button can return here.
 */
import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import { closesIn, formatDate } from '../../utils/deadline.js';
import { matchSummary } from '../../utils/matchSummary.js';
import ScoreBreakdown from '../ui/ScoreBreakdown.jsx';
import SkillChip, { skillState } from '../ui/SkillChip.jsx';
import StatusBadge from '../ui/StatusBadge.jsx';
import UnitComparisonTable from './UnitComparisonTable.jsx';

export default function RecommendationCard({ rec, rank, isTop = false, from }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();              // links the toggle button to the panel it opens
  const deadline = closesIn(rec.application_deadline);

  return (
    <article className={`rec-card ${isTop ? 'rec-card--top' : ''}`} aria-label={`Rank ${rank}: ${rec.title}`}>
      {isTop && <span className="rec-card__ribbon">★ Top match</span>}
      <div className="rec-card__head">
        <span className="rec-card__rank" aria-label={`Rank ${rank}`}>{rank}</span>
        <div className="rec-card__info">
          <h3 className="rec-card__title">{rec.title}</h3>
          <p className="muted small">
            {rec.organization} · {rec.sector} · {rec.location}
          </p>
          <p className={`small ${deadline.urgent ? 'deadline--urgent' : 'muted'}`}>
            Deadline {formatDate(rec.application_deadline)} ({deadline.label})
          </p>
          <div className="rec-card__tags">
            <StatusBadge eligible={rec.meets_requirements} />
            {rec.interest_match && <span className="tag tag--interest">♥ Interest match</span>}
            {rec.my_application && <span className="tag tag--applied">✓ Applied</span>}
          </div>
        </div>
        <div className="rec-card__score" aria-label={`Match ${Math.round(rec.match_percent)} percent`}>
          <span className="rec-card__percent">{Math.round(rec.match_percent)}%</span>
          <span className="muted small">match</span>
        </div>
      </div>

      <ScoreBreakdown breakdown={rec.breakdown} />

      <div className="rec-card__actions">
        <button type="button" className="btn btn--secondary btn--sm" aria-expanded={open}
          aria-controls={panelId} onClick={() => setOpen(!open)}>
          {open ? 'Hide details' : 'Why this match?'}
        </button>
        <Link className="btn btn--primary btn--sm" to={`/student/opportunities/${rec.opportunity_id}`}
          state={{ from }}>
          View details
        </Link>
      </div>

      {open && (
        <div id={panelId} className="rec-card__why">
          <p className="why-summary">{matchSummary(rec)}</p>
          {rec.units?.length > 0 && <UnitComparisonTable units={rec.units} />}
          {rec.skills?.length > 0 && (
            <div className="chips" aria-label="Required skills">
              {rec.skills.map((s) => (
                <SkillChip key={s.skill_id} name={s.skill} state={skillState(s)}
                  essential={s.importance === 'essential'} />
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
