import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { parseApiError } from '../../api/client.js';
import { closeOpportunity, fetchMyOpportunities } from '../../api/opportunities.js';
import DashboardLayout from '../../components/DashboardLayout.jsx';
import { PARTNER_NAV } from './partnerNav.js';

/** Compact requirement summary, e.g. "Computer Networks★ ≥55". ★ marks an essential unit. */
function RequirementChips({ requirements }) {
  return (
    <div className="chips">
      {requirements.map((r) => (
        <span
          key={r.unit_id}
          className={`chip ${r.importance === 'essential' ? 'chip--essential' : ''}`}
          title={`${r.unit_name} (${r.importance}${r.min_mark != null ? `, min ${r.min_mark}` : ''})`}
        >
          {r.unit_name}
          {r.importance === 'essential' && '★'}
          {r.min_mark != null && <small> ≥{r.min_mark}</small>}
        </span>
      ))}
    </div>
  );
}

export default function MyOpportunities() {
  const location = useLocation();
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState(null); // null = loading
  const [error, setError] = useState('');
  // Flash message from the create/edit page, shown once.
  const [notice, setNotice] = useState(location.state?.message || '');

  useEffect(() => {
    if (location.state?.message) navigate(location.pathname, { replace: true, state: null });
    fetchMyOpportunities()
      .then(setOpportunities)
      .catch((err) => setError(parseApiError(err).message));
    // Run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClose = async (opp) => {
    if (!window.confirm(`Close "${opp.title}"? Students will no longer see or be matched to it.`)) return;
    try {
      const updated = await closeOpportunity(opp.opportunity_id);
      setOpportunities((list) => list.map((o) => (o.opportunity_id === updated.opportunity_id ? updated : o)));
      setNotice(`"${updated.title}" is now closed.`);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <DashboardLayout title="Industry partner dashboard" nav={PARTNER_NAV}>
      {notice && <div className="alert alert--success">{notice}</div>}
      {error && <div className="alert alert--error">{error}</div>}

      {opportunities === null && !error && <p className="muted">Loading…</p>}

      {opportunities?.length === 0 && (
        <div className="panel empty">
          <p>You haven't posted any opportunities yet.</p>
          <Link className="btn btn--primary" to="/partner/opportunities/new">Post your first opportunity</Link>
        </div>
      )}

      {opportunities?.length > 0 && (
        <div className="panel panel--flush">
          <table className="table">
            <thead>
              <tr>
                <th>Opportunity</th>
                <th>Status</th>
                <th>Deadline</th>
                <th>Slots</th>
                <th>Requirements</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {opportunities.map((o) => (
                <tr key={o.opportunity_id}>
                  {/* data-label feeds the stacked mobile layout (see .table in global.css) */}
                  <td data-label="Opportunity">
                    <strong>{o.title}</strong>
                    <div className="muted small">{o.sector} · {o.location}</div>
                  </td>
                  <td data-label="Status">
                    <span className={`badge badge--${o.status}`}>{o.status}</span>
                  </td>
                  <td data-label="Deadline">{o.application_deadline ?? '—'}</td>
                  <td data-label="Slots">{o.slots}</td>
                  <td data-label="Requirements"><RequirementChips requirements={o.requirements} /></td>
                  <td className="actions">
                    <Link className="btn btn--secondary btn--sm" to={`/partner/opportunities/${o.opportunity_id}/edit`}>
                      Edit
                    </Link>
                    <button
                      type="button"
                      className="btn btn--danger btn--sm"
                      onClick={() => handleClose(o)}
                      disabled={o.status === 'closed'}
                    >
                      Close
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DashboardLayout>
  );
}
