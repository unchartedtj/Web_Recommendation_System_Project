/**
 * My Applications (/student/applications).
 *
 * One card per application: internship, company, applied date, match % at apply time,
 * status badge and a simple timeline. Rejected/withdrawn cards show the reason, active ones
 * can be withdrawn, and an accepted one shows the placement details.
 * The status filter is kept in the URL (?status=shortlisted) so Back restores it.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchMyApplications, withdrawApplication } from '../../api/applications.js';
import { parseApiError } from '../../api/client.js';
import StudentLayout from '../../components/student/StudentLayout.jsx';
import ApplicationStatusBadge, { STATUS_LABELS } from '../../components/ui/ApplicationStatusBadge.jsx';
import ConfirmDialog from '../../components/ui/ConfirmDialog.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import StatusTimeline from '../../components/ui/StatusTimeline.jsx';
import Toast from '../../components/ui/Toast.jsx';
import { formatDate } from '../../utils/deadline.js';

function PlacementPanel({ placement }) {
  return (
    <div className="placement-panel">
      <h4><span aria-hidden="true">🎉 </span>Your placement</h4>
      <dl>
        <div><dt>Company</dt><dd>{placement.organization}</dd></div>
        <div><dt>Status</dt><dd className="capitalize">{placement.status}</dd></div>
        <div><dt>Start date</dt><dd>{formatDate(placement.start_date)}</dd></div>
        <div><dt>End date</dt><dd>{formatDate(placement.end_date)}</dd></div>
      </dl>
    </div>
  );
}

function ApplicationCard({ app, onWithdraw }) {
  const o = app.opportunity;
  const active = app.status === 'pending' || app.status === 'shortlisted';
  return (
    <article className={`panel app-card app-card--${app.status}`}>
      <div className="app-card__head">
        <div>
          <h3 className="app-card__title">{o.title}</h3>
          <p className="muted small">{o.organization} · {o.sector}</p>
        </div>
        <ApplicationStatusBadge status={app.status} />
      </div>
      <ul className="app-card__facts">
        <li><span className="muted">Applied</span> {formatDate(app.application_date)}</li>
        <li><span className="muted">Match when applied</span> {Math.round(app.match_percent_at_apply ?? 0)}%</li>
      </ul>
      <StatusTimeline status={app.status} />
      {app.status_reason && (
        <p className="app-card__reason"><span className="muted">Reason:</span> {app.status_reason}</p>
      )}
      {app.placement && <PlacementPanel placement={app.placement} />}
      <div className="app-card__actions">
        {o.status === 'open' && (
          <Link className="btn btn--secondary btn--sm" to={`/student/opportunities/${o.opportunity_id}`}
            state={{ from: '/student/applications' }}>View internship</Link>
        )}
        {active && (
          <button type="button" className="btn btn--danger btn--sm" onClick={() => onWithdraw(app)}>
            Withdraw
          </button>
        )}
      </div>
    </article>
  );
}

export default function MyApplications() {
  const [params, setParams] = useSearchParams();
  const status = params.get('status') ?? '';
  const [apps, setApps] = useState(null);   // null = loading
  const [error, setError] = useState('');
  const [confirming, setConfirming] = useState(null);
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState('');
  const [toast, setToast] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  const load = useCallback(() => {
    setError('');
    setApps(null);
    fetchMyApplications(status || undefined)
      .then(setApps)
      .catch((err) => setError(parseApiError(err).message));
  }, [status]);
  useEffect(load, [load]);

  const doWithdraw = async () => {
    setBusy(true);
    setDialogError('');
    try {
      await withdrawApplication(confirming.application_id);
      setConfirming(null);
      setToast('Application withdrawn');
      load();
    } catch (err) {
      setDialogError(parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <StudentLayout>
      <div className="page-head">
        <div>
          <h1>My applications</h1>
          <p className="muted">Track every internship you&apos;ve applied to.</p>
        </div>
      </div>

      <div className="filter-row" role="group" aria-label="Filter applications">
        <div className="field">
          <label htmlFor="app-status">Status</label>
          <select id="app-status" value={status}
            onChange={(e) => setParams(e.target.value ? { status: e.target.value } : {})}>
            <option value="">All</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={load} />
      {apps === null && !error && <LoadingSkeleton variant="cards" count={2} />}

      {apps?.length === 0 && (
        <EmptyState icon="📝" title={status ? 'No applications with this status' : 'No applications yet'}
          action={<Link className="btn btn--primary" to="/student/recommendations">See your recommendations</Link>}>
          Find an internship that matches you and apply from its details page.
        </EmptyState>
      )}

      {apps?.length > 0 && (
        <div className="app-list">
          {apps.map((a) => (
            <ApplicationCard key={a.application_id} app={a}
              onWithdraw={(app) => { setDialogError(''); setConfirming(app); }} />
          ))}
        </div>
      )}

      {confirming && (
        <ConfirmDialog title="Withdraw application?" confirmLabel="Withdraw" danger busy={busy}
          error={dialogError} onConfirm={doWithdraw} onCancel={() => setConfirming(null)}>
          <p>
            Withdraw your application to <strong>{confirming.opportunity.title}</strong>? You
            won&apos;t be able to apply to this internship again.
          </p>
        </ConfirmDialog>
      )}
      <Toast message={toast} onDone={clearToast} />
    </StudentLayout>
  );
}
