/**
 * One student's read-only record (/admin/students/:id): profile, grades, skills, interests,
 * current top recommendations, applications and placement.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchStudent } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import { ActivePill, PlacementStatusPill } from '../../components/admin/Pill.jsx';
import ApplicationStatusBadge from '../../components/ui/ApplicationStatusBadge.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import MatchBar from '../../components/ui/MatchBar.jsx';
import ScoreBreakdown from '../../components/ui/ScoreBreakdown.jsx';
import SkillChip from '../../components/ui/SkillChip.jsx';
import StatusBadge from '../../components/ui/StatusBadge.jsx';
import { formatDate } from '../../utils/deadline.js';

export default function AdminStudentDetail() {
  const { id } = useParams();
  const [s, setS] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    fetchStudent(id).then(setS).catch((err) => setError(parseApiError(err).message));
  }, [id]);
  useEffect(load, [load]);

  return (
    <AdminLayout title={s ? s.name : 'Student'}>
      <Link className="btn btn--secondary btn--sm back-btn" to="/admin/students">← All students</Link>
      <ErrorBanner message={error} onRetry={load} />
      {!s && !error && <LoadingSkeleton variant="cards" count={2} />}
      {s && (
        <div className="record-grid">
          <section className="panel">
            <h2 className="small-heading">Profile</h2>
            <dl className="detail-list">
              <div><dt>Email</dt><dd>{s.email}</dd></div>
              <div><dt>Admission no</dt><dd>{s.admission_no}</dd></div>
              <div><dt>Course</dt><dd>{s.course}, year {s.year_of_study}</dd></div>
              <div><dt>Account</dt><dd><ActivePill active={s.is_active} /></dd></div>
              <div><dt>Profile</dt><dd>{s.profile_complete ? 'Complete' : 'Incomplete'}
                {s.profile_updated_at && ` (updated ${formatDate(s.profile_updated_at)})`}</dd></div>
            </dl>
            <h3 className="small-heading">Skills</h3>
            <div className="chips">
              {s.skills.length ? s.skills.map((k) => <SkillChip key={k} name={k} />) : <span className="muted">None</span>}
            </div>
            <h3 className="small-heading">Career interests</h3>
            <p>{s.interests.length ? s.interests.join(', ') : <span className="muted">None</span>}</p>
          </section>

          <section className="panel">
            <h2 className="small-heading">Grades</h2>
            {s.grades.length === 0 ? <p className="muted">No grades entered yet.</p> : (
              <table className="table compact-table">
                <thead><tr><th>Unit</th><th>Mark</th></tr></thead>
                <tbody>
                  {s.grades.map((g) => (
                    <tr key={g.unit_id}><td data-label="Unit">{g.unit}</td><td data-label="Mark">{g.mark}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="panel">
            <h2 className="small-heading">Placement</h2>
            {s.placement ? (
              <dl className="detail-list">
                <div><dt>Status</dt><dd><PlacementStatusPill status={s.placement.status} /></dd></div>
                <div><dt>Internship</dt><dd>{s.placement.internship} · {s.placement.company}</dd></div>
                <div><dt>Dates</dt><dd>{formatDate(s.placement.start_date)} to {formatDate(s.placement.end_date)}</dd></div>
              </dl>
            ) : <p className="muted">No placement yet.</p>}
            <h3 className="small-heading">Applications</h3>
            {s.applications_list.length === 0 ? <p className="muted">No applications.</p> : (
              <ul className="plain-list">
                {s.applications_list.map((a) => (
                  <li key={a.application_id}>
                    <strong>{a.opportunity.title}</strong> · {a.opportunity.organization}{' '}
                    <ApplicationStatusBadge status={a.status} />
                    <span className="muted small"> {Math.round(a.match_percent_at_apply ?? 0)}% when applied</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel record-grid__wide">
            <h2 className="small-heading">Current top recommendations</h2>
            {s.top_recommendations.length === 0 ? <p className="muted">None (profile incomplete).</p> : (
              <div className="mini-cards">
                {s.top_recommendations.map((r) => (
                  <div key={r.opportunity_id} className="mini-card">
                    <span className="mini-card__rank">#{r.rank}</span>
                    <strong>{r.title}</strong>
                    <span className="muted small">{r.organization}</span>
                    <MatchBar percent={r.match_percent} size="sm" />
                    <StatusBadge eligible={r.meets_requirements} />
                    <ScoreBreakdown breakdown={r.breakdown} />
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </AdminLayout>
  );
}
