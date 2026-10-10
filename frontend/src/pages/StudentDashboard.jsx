/**
 * Student dashboard (/student).
 *   - "Welcome, <first name>"
 *   - profile status card (complete / incomplete, last updated, button)
 *   - quick stats: open internships, how many you're eligible for, your top match %
 *   - "Your top 3 matches" (compact cards linking to details) + "See all recommendations"
 * Empty states guide students who haven't completed their profile yet.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { parseApiError } from '../api/client.js';
import { fetchOpportunities, fetchProfile, fetchRecommendations } from '../api/student.js';
import StudentLayout from '../components/student/StudentLayout.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import ErrorBanner from '../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../components/ui/LoadingSkeleton.jsx';
import MatchBar from '../components/ui/MatchBar.jsx';
import StatusBadge from '../components/ui/StatusBadge.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { formatDate } from '../utils/deadline.js';

export default function StudentDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);   // { profile, recs, openCount }; null = loading
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    setData(null);
    Promise.all([fetchProfile(), fetchRecommendations(), fetchOpportunities()])
      .then(([profile, recs, browse]) => setData({ profile, recs, openCount: browse.opportunities.length }))
      .catch((err) => setError(parseApiError(err).message));
  }, []);
  useEffect(load, [load]);

  const firstName = user?.profile?.first_name ?? user?.name ?? '';
  const eligible = data?.recs.eligible ?? [];
  const all = data ? [...eligible, ...data.recs.not_eligible] : [];
  const top3 = all.slice(0, 3);
  const topPercent = all.length ? Math.round(all[0].match_percent) : null;
  const complete = data?.profile.is_complete;

  return (
    <StudentLayout>
      <h1>Welcome, {firstName}</h1>
      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && <LoadingSkeleton variant="cards" count={2} />}

      {data && (
        <>
          {/* ---- Profile status ---- */}
          <section className={`panel status-card ${complete ? '' : 'status-card--todo'}`}
            aria-labelledby="profile-status">
            <div>
              <h2 id="profile-status">
                {complete ? '✓ Your profile is complete' : 'Your profile is incomplete'}
              </h2>
              <p className="muted">
                {complete
                  ? `Last updated ${formatDate(data.profile.profile_updated_at)}. Update it whenever your marks, skills or interests change.`
                  : 'Add your marks for the 12 units, your technical skills and up to 3 career interests to get recommendations.'}
              </p>
            </div>
            <Link className="btn btn--primary" to="/student/profile">
              {complete ? 'Update profile' : 'Complete your profile'}
            </Link>
          </section>

          {/* ---- Quick stats ---- */}
          <ul className="stats" aria-label="Quick stats">
            <li className="stat"><span className="stat__value">{data.openCount}</span>
              <span className="stat__label">Open internships</span></li>
            <li className="stat"><span className="stat__value">{complete ? eligible.length : '—'}</span>
              <span className="stat__label">You're eligible for</span></li>
            <li className="stat"><span className="stat__value">{topPercent !== null ? `${topPercent}%` : '—'}</span>
              <span className="stat__label">Your top match</span></li>
          </ul>

          {/* ---- Top 3 matches ---- */}
          <section aria-labelledby="top-matches">
            <div className="page-head">
              <h2 id="top-matches" className="section-title">Your top 3 matches</h2>
              {top3.length > 0 && (
                <Link className="btn btn--secondary btn--sm" to="/student/recommendations">See all recommendations</Link>
              )}
            </div>
            {top3.length === 0 ? (
              <EmptyState icon="🧭" title="No matches yet"
                action={<Link className="btn btn--primary" to="/student/profile">Complete your profile</Link>}>
                Once your profile is complete, your best-matching internships appear here.
              </EmptyState>
            ) : (
              <div className="mini-cards">
                {top3.map((r, i) => (
                  <Link key={r.opportunity_id} className="mini-card" to={`/student/opportunities/${r.opportunity_id}`}
                    state={{ from: '/student' }}>
                    <span className="mini-card__rank">#{i + 1}</span>
                    <strong>{r.title}</strong>
                    <span className="muted small">{r.organization}</span>
                    <MatchBar percent={r.match_percent} size="sm" />
                    <StatusBadge eligible={r.meets_requirements} />
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </StudentLayout>
  );
}
