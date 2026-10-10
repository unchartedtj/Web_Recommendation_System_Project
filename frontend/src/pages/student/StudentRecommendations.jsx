/**
 * "Your recommended placements" (/student/recommendations).
 *
 * Two sections, each in descending match score:
 *   1. "You meet the requirements"     – eligible internships (#1 is the highlighted Top match)
 *   2. "Below minimum requirements"    – collapsed by default ("2 more internships")
 * Filters (sector, "Eligible only") live in the URL (?sector=3&eligible=1), so the details
 * page's Back button returns to exactly this view. Filtering only HIDES cards; it never
 * changes their order or rank numbers.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { parseApiError } from '../../api/client.js';
import { fetchRecommendations } from '../../api/student.js';
import RecommendationCard from '../../components/student/RecommendationCard.jsx';
import StudentLayout from '../../components/student/StudentLayout.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import { formatDate } from '../../utils/deadline.js';

/** Best match first. Array.sort is stable, so equal scores keep the API's order. */
const byScore = (list) => [...list].sort((a, b) => b.match_score - a.match_score);

export default function StudentRecommendations() {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState(null);          // null = loading
  const [error, setError] = useState('');
  const [showBelow, setShowBelow] = useState(false);

  const load = useCallback(() => {
    setError('');
    setData(null);
    fetchRecommendations().then(setData).catch((err) => setError(parseApiError(err).message));
  }, []);
  useEffect(load, [load]);

  const sectorFilter = params.get('sector') ?? '';
  const eligibleOnly = params.get('eligible') === '1';
  const setFilter = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };

  // Rank numbers come from the UNFILTERED lists: eligible 1..k, then below-minimum k+1..n.
  const { eligible, below, sectors } = useMemo(() => {
    if (!data) return { eligible: [], below: [], sectors: [] };
    const e = byScore(data.eligible).map((r, i) => ({ ...r, displayRank: i + 1 }));
    const b = byScore(data.not_eligible).map((r, i) => ({ ...r, displayRank: e.length + i + 1 }));
    const seen = new Map([...e, ...b].map((r) => [String(r.sector_id), r.sector]));
    return { eligible: e, below: b, sectors: [...seen].sort((x, y) => x[1].localeCompare(y[1])) };
  }, [data]);

  // .filter keeps the original order, so filtering can never reorder cards.
  const matchesSector = (r) => !sectorFilter || String(r.sector_id) === sectorFilter;
  const shownEligible = eligible.filter(matchesSector);
  const shownBelow = eligibleOnly ? [] : below.filter(matchesSector);
  const here = `${location.pathname}${location.search}`;   // for the details page's Back button

  const empty = data && !data.profile_complete && eligible.length + below.length === 0;

  return (
    <StudentLayout>
      <div className="page-head">
        <div>
          <h1>Your recommended placements</h1>
          {data?.profile_updated_at && (
            <p className="muted">Profile last updated {formatDate(data.profile_updated_at)}</p>
          )}
        </div>
        <Link className="btn btn--secondary" to="/student/profile">Update profile</Link>
      </div>

      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && <LoadingSkeleton variant="cards" count={3} />}

      {empty && (
        <EmptyState icon="🧭" title="Complete your profile to see recommendations"
          action={<Link className="btn btn--primary" to="/student/profile">Complete your profile</Link>}>
          We match you to internships using your grades, skills and career interests.
        </EmptyState>
      )}

      {data && !empty && (
        <>
          {/* ---- Filters ---- */}
          <div className="filter-row" role="group" aria-label="Filter recommendations">
            <div className="field">
              <label htmlFor="rec-sector">Sector</label>
              <select id="rec-sector" value={sectorFilter} onChange={(e) => setFilter('sector', e.target.value)}>
                <option value="">All sectors</option>
                {sectors.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
              </select>
            </div>
            <label className="toggle">
              <input type="checkbox" checked={eligibleOnly}
                onChange={(e) => setFilter('eligible', e.target.checked ? '1' : '')} />
              Eligible only
            </label>
          </div>

          {/* ---- Section 1: eligible ---- */}
          <section aria-labelledby="sec-eligible">
            <h2 id="sec-eligible" className="section-title">
              You meet the requirements <span className="count">{shownEligible.length}</span>
            </h2>
            {shownEligible.length === 0 ? (
              <p className="muted">No eligible internships{sectorFilter ? ' in this sector' : ''} yet.</p>
            ) : (
              <div className="rec-list-cards" data-testid="eligible-list">
                {shownEligible.map((r) => (
                  <RecommendationCard key={r.opportunity_id} rec={r} rank={r.displayRank}
                    isTop={r.displayRank === 1} from={here} />
                ))}
              </div>
            )}
          </section>

          {/* ---- Section 2: below minimum (collapsed by default) ---- */}
          {!eligibleOnly && below.filter(matchesSector).length > 0 && (
            <section aria-labelledby="sec-below" className="below-section">
              <h2 id="sec-below" className="section-title">Below minimum requirements</h2>
              <button type="button" className="btn btn--secondary" aria-expanded={showBelow}
                aria-controls="below-list" onClick={() => setShowBelow(!showBelow)}>
                {showBelow ? 'Hide' : 'Show'} {shownBelow.length} more
                {shownBelow.length === 1 ? ' internship' : ' internships'}
              </button>
              {showBelow && (
                <div id="below-list" className="rec-list-cards" data-testid="below-list">
                  <p className="muted small">
                    Your mark is below an essential minimum for these. They're shown so you can see
                    what to improve.
                  </p>
                  {shownBelow.map((r) => (
                    <RecommendationCard key={r.opportunity_id} rec={r} rank={r.displayRank} from={here} />
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}
    </StudentLayout>
  );
}
