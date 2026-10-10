/**
 * Internship details (/student/opportunities/:id).
 *
 * Shows everything about the internship, the requirements next to the student's own marks
 * and skills, and a "Your match" panel (or a prompt to complete the profile).
 * Back returns to wherever the student came from (recommendations or browse, with their
 * filters), using the `from` URL those pages pass along when linking here.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { parseApiError } from '../../api/client.js';
import { fetchOpportunity } from '../../api/student.js';
import StudentLayout from '../../components/student/StudentLayout.jsx';
import UnitComparisonTable from '../../components/student/UnitComparisonTable.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import MatchBar from '../../components/ui/MatchBar.jsx';
import ScoreBreakdown from '../../components/ui/ScoreBreakdown.jsx';
import SkillChip, { skillState } from '../../components/ui/SkillChip.jsx';
import StatusBadge from '../../components/ui/StatusBadge.jsx';
import { closesIn, formatDate } from '../../utils/deadline.js';
import { matchSummary } from '../../utils/matchSummary.js';

export default function OpportunityDetails() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [data, setData] = useState(null);     // null = loading
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(() => {
    setError('');
    setData(null);
    fetchOpportunity(id)
      .then(setData)
      .catch((err) => {
        if (err.response?.status === 404) setNotFound(true);
        else setError(parseApiError(err).message);
      });
  }, [id]);
  useEffect(load, [load]);

  const goBack = () => navigate(location.state?.from ?? '/student/opportunities');
  const backLabel = location.state?.from?.startsWith('/student/recommendations')
    ? 'Back to recommendations' : 'Back to internships';

  const o = data?.opportunity;
  const m = data?.my_match;
  const deadline = o ? closesIn(o.application_deadline) : null;

  return (
    <StudentLayout>
      <button type="button" className="btn btn--secondary btn--sm back-btn" onClick={goBack}>
        <span aria-hidden="true">← </span>{backLabel}
      </button>

      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && !notFound && <LoadingSkeleton variant="cards" count={2} />}

      {notFound && (
        <EmptyState icon="🚫" title="This internship isn't available"
          action={<Link className="btn btn--primary" to="/student/opportunities">Browse internships</Link>}>
          It may have been closed by the company.
        </EmptyState>
      )}

      {o && (
        <div className="details">
          <div className="details__main">
            <header className="details__header">
              <h1>{o.title}</h1>
              <p className="details__company">{o.organization_name} · {o.sector}</p>
              <ul className="details__facts">
                <li><span className="muted">Location</span>{o.location}</li>
                <li><span className="muted">Duration</span>{o.duration_months} months</li>
                <li><span className="muted">Slots</span>{o.slots}</li>
                <li><span className="muted">Posted</span>{formatDate(o.date_posted)}</li>
                <li className={deadline.urgent ? 'deadline--urgent' : ''}>
                  <span className="muted">Deadline</span>
                  {formatDate(o.application_deadline)} ({deadline.label})
                </li>
              </ul>
            </header>

            <section className="panel">
              <h2>About the internship</h2>
              <p className="details__description">{o.description}</p>
            </section>

            <section className="panel">
              <h2>Requirements</h2>
              <h3>Units</h3>
              <UnitComparisonTable units={m ? m.units : o.requirements} showMine={Boolean(m)} />
              <h3>Skills</h3>
              <div className="chips">
                {(m ? m.skills : o.skills.map((s) => ({ ...s, skill: s.name }))).map((s) => (
                  <SkillChip key={s.skill_id} name={s.skill} state={skillState(s)}
                    essential={s.importance === 'essential'} />
                ))}
              </div>
            </section>
          </div>

          <aside className="details__side">
            {m ? (
              <section className="panel match-panel" aria-labelledby="your-match">
                <h2 id="your-match">Your match</h2>
                <MatchBar percent={m.match_percent} size="lg" />
                <StatusBadge eligible={m.meets_requirements} />
                {m.interest_match && <span className="tag tag--interest">♥ Interest match</span>}
                <ScoreBreakdown breakdown={m.breakdown} />
                <p className="why-summary">{matchSummary({ ...m, sector: o.sector })}</p>
              </section>
            ) : (
              <section className="panel match-panel">
                <h2>Your match</h2>
                <p className="muted">Complete your profile to see how well you match this internship.</p>
                <Link className="btn btn--primary" to="/student/profile">Complete your profile</Link>
              </section>
            )}

            {/* ============================================================
                APPLY BUTTON PLACEHOLDER: built in the next step (applications).
                Do not show a button here yet.
               ============================================================ */}
            <div className="apply-slot" data-slot="apply" />
          </aside>
        </div>
      )}
    </StudentLayout>
  );
}
