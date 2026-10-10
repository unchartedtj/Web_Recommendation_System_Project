/**
 * "Browse Internships" (/student/opportunities).
 *
 * Search box, sector, skill and sort controls. They're all kept in the URL
 * (?search=data&sector_id=3&skill_id=8&sort=deadline), so the details page's Back button
 * returns here with the same filters. "Best match" is offered only when the student's
 * profile is complete. Typing in the search box waits 350 ms before searching ("debounce"),
 * so we don't call the API on every keystroke.
 */
import { useCallback, useEffect, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { fetchSectors, fetchSkillCategories } from '../../api/catalog.js';
import { parseApiError } from '../../api/client.js';
import { fetchOpportunities } from '../../api/student.js';
import OpportunityCard from '../../components/student/OpportunityCard.jsx';
import StudentLayout from '../../components/student/StudentLayout.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';

const FILTER_KEYS = ['search', 'sector_id', 'skill_id', 'sort'];

export default function BrowseOpportunities() {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? '']));

  const [searchText, setSearchText] = useState(filters.search);
  const [sectors, setSectors] = useState([]);
  const [skillCategories, setSkillCategories] = useState([]);
  const [data, setData] = useState(null);           // null = loading
  const [error, setError] = useState('');

  const setFilter = useCallback((key, value) => {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value); else next.delete(key);
      return next;
    }, { replace: true });
  }, [setParams]);

  // Dropdown options (loaded once).
  useEffect(() => {
    fetchSectors().then(setSectors).catch(() => {});
    fetchSkillCategories().then(setSkillCategories).catch(() => {});
  }, []);

  // Debounce: update the URL's search 350 ms after the student stops typing.
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchText.trim() !== filters.search) setFilter('search', searchText.trim());
    }, 350);
    return () => clearTimeout(timer);
  }, [searchText, filters.search, setFilter]);

  // Fetch whenever the filters in the URL change.
  const query = params.toString();
  const load = useCallback(() => {
    setError('');
    setData(null);
    fetchOpportunities(Object.fromEntries(new URLSearchParams(query)))
      .then(setData)
      .catch((err) => setError(parseApiError(err).message));
  }, [query]);
  useEffect(load, [load]);

  const clearFilters = () => {
    setSearchText('');
    setParams(new URLSearchParams(), { replace: true });
  };
  const hasFilters = FILTER_KEYS.some((k) => k !== 'sort' && filters[k]);
  const here = `${location.pathname}${location.search}`;

  return (
    <StudentLayout>
      <div className="page-head">
        <h1>Browse internships</h1>
      </div>

      <div className="filter-row filter-row--browse" role="search">
        <div className="field filter-row__search">
          <label htmlFor="browse-search">Search</label>
          <input id="browse-search" type="search" placeholder="Title or company"
            value={searchText} onChange={(e) => setSearchText(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="browse-sector">Sector</label>
          <select id="browse-sector" value={filters.sector_id} onChange={(e) => setFilter('sector_id', e.target.value)}>
            <option value="">All sectors</option>
            {sectors.map((s) => <option key={s.sector_id} value={s.sector_id}>{s.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="browse-skill">Skill</label>
          <select id="browse-skill" value={filters.skill_id} onChange={(e) => setFilter('skill_id', e.target.value)}>
            <option value="">Any skill</option>
            {skillCategories.map((c) => (
              <optgroup key={c.category} label={c.category}>
                {c.skills.map((s) => <option key={s.skill_id} value={s.skill_id}>{s.name}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="browse-sort">Sort by</label>
          <select id="browse-sort" value={data?.sort ?? (filters.sort || 'newest')}
            onChange={(e) => setFilter('sort', e.target.value === 'newest' ? '' : e.target.value)}>
            <option value="newest">Newest</option>
            <option value="deadline">Deadline soonest</option>
            {data?.profile_complete && <option value="best_match">Best match</option>}
          </select>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && <LoadingSkeleton variant="cards" count={6} />}

      {data && data.opportunities.length === 0 && (
        <EmptyState icon="🔍" title="No internships match your filters"
          action={hasFilters && (
            <button type="button" className="btn btn--primary" onClick={clearFilters}>Clear filters</button>
          )}>
          Try a different search, or remove a filter.
        </EmptyState>
      )}

      {data && data.opportunities.length > 0 && (
        <>
          <p className="muted small" aria-live="polite">
            {data.opportunities.length} internship{data.opportunities.length === 1 ? '' : 's'}
            {!data.profile_complete && ' · complete your profile to see your match for each one'}
          </p>
          <div className="opp-grid">
            {data.opportunities.map((o) => <OpportunityCard key={o.opportunity_id} opp={o} from={here} />)}
          </div>
        </>
      )}
    </StudentLayout>
  );
}
