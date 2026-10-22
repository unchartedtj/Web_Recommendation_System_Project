/**
 * Candidates for one opportunity (/partner/opportunities/:id/candidates).
 *
 * Header: title, slots filled x/y, status and deadline. Filter tabs with counts
 * (kept in the URL, e.g. ?status=pending). Candidate cards are sorted by match % (best first).
 * Shortlist / Accept (optional start + end dates) / Reject (optional reason) each ask for
 * confirmation. If something changed meanwhile (e.g. the slots just filled), the API error
 * is shown and the list reloads.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { parseApiError } from '../../api/client.js';
import { decideApplication, fetchCandidates } from '../../api/opportunities.js';
import DashboardLayout from '../../components/DashboardLayout.jsx';
import CandidateCard from '../../components/partner/CandidateCard.jsx';
import ConfirmDialog from '../../components/ui/ConfirmDialog.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import Toast from '../../components/ui/Toast.jsx';
import { formatDate } from '../../utils/deadline.js';
import { PARTNER_NAV } from './partnerNav.js';

// [URL value, tab label, key in `counts`]
const TABS = [
  ['', 'All', 'all'], ['pending', 'Pending', 'pending'], ['shortlisted', 'Shortlisted', 'shortlisted'],
  ['accepted', 'Accepted', 'accepted'], ['rejected', 'Rejected', 'rejected'],
  ['withdrawn', 'Withdrawn', 'withdrawn'],
];

const DIALOG = {
  shortlist: { title: 'Shortlist candidate?', label: 'Shortlist', done: 'shortlisted' },
  accept: { title: 'Accept candidate?', label: 'Accept', done: 'accepted' },
  reject: { title: 'Reject candidate?', label: 'Reject', done: 'rejected', danger: true },
};

export default function Candidates() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const status = params.get('status') ?? '';
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(null);       // {action, candidate} awaiting confirmation
  const [form, setForm] = useState({ reason: '', start_date: '', end_date: '' });
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState('');
  const [toast, setToast] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  const load = useCallback(() => {
    fetchCandidates(id, status || undefined)
      .then(setData)
      .catch((err) => setError(parseApiError(err).message));
  }, [id, status]);
  useEffect(() => { setData(null); setError(''); load(); }, [load]);

  const openDialog = (action, candidate) => {
    setForm({ reason: '', start_date: '', end_date: '' });
    setDialogError('');
    setPending({ action, candidate });
  };

  const confirm = async () => {
    const { action, candidate } = pending;
    const body = { action };
    if (action === 'reject' && form.reason.trim()) body.reason = form.reason.trim();
    if (action === 'accept') {
      if (form.start_date) body.start_date = form.start_date;
      if (form.end_date) body.end_date = form.end_date;
    }
    setBusy(true);
    setDialogError('');
    try {
      await decideApplication(candidate.application_id, body);
      setPending(null);
      setError('');
      setToast(`${candidate.student.name} ${DIALOG[action].done}`);
      load();
    } catch (err) {
      const { message, fields } = parseApiError(err);
      if (err.response?.status === 400) {
        // A field problem (e.g. end date before start date): keep the dialog open.
        setDialogError(Object.values(fields)[0] ?? message);
      } else {
        // A conflict (e.g. the slots just filled): show it on the page and refresh the list.
        setPending(null);
        setError(message);
        load();
      }
    } finally {
      setBusy(false);
    }
  };

  const o = data?.opportunity;
  const counts = data?.counts ?? {};
  // Best match first (the API sends them sorted, but the page doesn't rely on it).
  const candidates = [...(data?.candidates ?? [])]
    .sort((a, b) => (b.match_score ?? 0) - (a.match_score ?? 0) || a.application_id - b.application_id);

  return (
    <DashboardLayout title="Industry partner dashboard" nav={PARTNER_NAV}>
      <Link className="btn btn--secondary btn--sm back-btn" to="/partner">
        <span aria-hidden="true">← </span>Back to my opportunities
      </Link>

      {o && (
        <header className="candidates-head">
          <h1>{o.title}</h1>
          <ul className="details__facts">
            <li><span className="muted">Slots filled</span>{o.slots_filled}/{o.slots}</li>
            <li><span className="muted">Status</span><span className={`badge badge--${o.status}`}>{o.status}</span></li>
            <li><span className="muted">Deadline</span>{formatDate(o.application_deadline)}</li>
          </ul>
        </header>
      )}

      <ErrorBanner message={error} onRetry={load} />

      {o && (
        <div className="tabs" role="group" aria-label="Filter by status">
          {TABS.map(([value, label, key]) => (
            <button key={key} type="button" aria-pressed={status === value}
              className={`tab${status === value ? ' tab--active' : ''}`}
              onClick={() => setParams(value ? { status: value } : {})}>
              {label} <span className="count">{counts[key] ?? 0}</span>
            </button>
          ))}
        </div>
      )}

      {!data && !error && <LoadingSkeleton variant="cards" count={2} />}

      {data && candidates.length === 0 && (
        <EmptyState icon="📭" title={status ? 'No candidates with this status' : 'No applications yet'}>
          {status ? 'Try another tab.' : 'Students who apply to this internship will appear here.'}
        </EmptyState>
      )}

      {candidates.length > 0 && (
        <div className="candidate-list">
          {candidates.map((c, i) => (
            <CandidateCard key={c.application_id} candidate={c} rank={i + 1} onAction={openDialog} />
          ))}
        </div>
      )}

      {pending && (
        <ConfirmDialog title={DIALOG[pending.action].title} confirmLabel={DIALOG[pending.action].label}
          danger={DIALOG[pending.action].danger} busy={busy} error={dialogError}
          onConfirm={confirm} onCancel={() => setPending(null)}>
          <p>
            {DIALOG[pending.action].label} <strong>{pending.candidate.student.name}</strong>
            {' '}({Math.round(pending.candidate.match_percent ?? 0)}% match)?
          </p>
          {pending.action === 'accept' && (
            <>
              <p className="muted small">
                This creates a confirmed placement. The student&apos;s other applications are
                withdrawn, and when all slots are filled the internship closes.
              </p>
              <div className="field">
                <label htmlFor="start-date">Start date (optional)</label>
                <input id="start-date" type="date" value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="end-date">End date (optional)</label>
                <input id="end-date" type="date" value={form.end_date}
                  onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
              </div>
            </>
          )}
          {pending.action === 'reject' && (
            <div className="field">
              <label htmlFor="reject-reason">Reason (optional, shown to the student)</label>
              <textarea id="reject-reason" rows={3} maxLength={255} value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            </div>
          )}
        </ConfirmDialog>
      )}
      <Toast message={toast} onDone={clearToast} />
    </DashboardLayout>
  );
}
