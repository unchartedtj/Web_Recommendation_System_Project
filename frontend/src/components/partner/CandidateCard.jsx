/**
 * One applicant on the partner's Candidates page.
 * Summary: name, course, year, match % + breakdown, eligibility (at apply time), applied date,
 * status. "Details" expands: unit comparison, skills have/missing, interests, the note, and the
 * email (only once shortlisted or accepted). Only the actions allowed right now are shown.
 */
import { useId, useState } from 'react';
import UnitComparisonTable from '../student/UnitComparisonTable.jsx';
import ApplicationStatusBadge from '../ui/ApplicationStatusBadge.jsx';
import MatchBar from '../ui/MatchBar.jsx';
import ScoreBreakdown from '../ui/ScoreBreakdown.jsx';
import SkillChip, { skillState } from '../ui/SkillChip.jsx';
import StatusBadge from '../ui/StatusBadge.jsx';
import { formatDate } from '../../utils/deadline.js';

export default function CandidateCard({ candidate: c, rank, onAction }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const s = c.student;
  const active = c.status === 'pending' || c.status === 'shortlisted';

  return (
    <article className={`panel candidate-card candidate-card--${c.status}`} data-testid="candidate">
      <div className="candidate-card__head">
        <span className="rec-card__rank" aria-label={`Rank ${rank}`}>{rank}</span>
        <div className="candidate-card__who">
          <h3 className="candidate-card__name">{s.name}</h3>
          <p className="muted small">{s.course} · Year {s.year_of_study} · Adm. {s.admission_no}</p>
          <p className="muted small">Applied {formatDate(c.application_date)}</p>
        </div>
        <div className="candidate-card__status">
          <ApplicationStatusBadge status={c.status} />
          <StatusBadge eligible={c.meets_requirements} />
        </div>
      </div>

      <MatchBar percent={c.match_percent} label={`${s.name} match`} />
      {c.breakdown && <ScoreBreakdown breakdown={c.breakdown} />}
      {c.status_reason && <p className="small"><span className="muted">Reason:</span> {c.status_reason}</p>}

      <div className="candidate-card__actions">
        <button type="button" className="btn btn--secondary btn--sm" aria-expanded={open}
          aria-controls={panelId} onClick={() => setOpen(!open)}>
          {open ? 'Hide details' : 'Details'}
        </button>
        {c.status === 'pending' && (
          <button type="button" className="btn btn--secondary btn--sm" onClick={() => onAction('shortlist', c)}>
            Shortlist
          </button>
        )}
        {active && (
          <>
            <button type="button" className="btn btn--primary btn--sm" onClick={() => onAction('accept', c)}>
              Accept
            </button>
            <button type="button" className="btn btn--danger btn--sm" onClick={() => onAction('reject', c)}>
              Reject
            </button>
          </>
        )}
      </div>

      {open && (
        <div id={panelId} className="candidate-card__details">
          <h4>Units (marks when they applied)</h4>
          <UnitComparisonTable units={c.units} mineLabel="Their mark" />
          <h4>Skills</h4>
          <div className="chips">
            {c.skills.map((sk) => (
              <SkillChip key={sk.skill_id} name={sk.skill} state={skillState(sk)}
                essential={sk.importance === 'essential'} />
            ))}
          </div>
          <h4>Career interests</h4>
          <p>
            {c.interests.length ? c.interests.join(', ') : '—'}
            {c.interest_match && <> <span className="tag tag--interest">♥ Matches this sector</span></>}
          </p>
          <h4>Motivation note</h4>
          <p className="candidate-card__note">{c.motivation_note || <span className="muted">No note.</span>}</p>
          <h4>Contact</h4>
          <p>
            {s.email
              ? <a href={`mailto:${s.email}`}>{s.email}</a>
              : <span className="muted">The email is shown once you shortlist this candidate.</span>}
          </p>
          {c.placement && (
            <p className="small">
              Placement {c.placement.status}: {formatDate(c.placement.start_date)} to {formatDate(c.placement.end_date)}
            </p>
          )}
        </div>
      )}
    </article>
  );
}
