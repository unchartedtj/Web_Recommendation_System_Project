/**
 * All opportunities (/admin/opportunities) with filters, and Close / Reopen actions.
 * Reopening is only offered when the deadline is still in the future and slots remain.
 */
import { useCallback, useEffect, useState } from 'react';
import { fetchAdminOpportunities, fetchPartners, setOpportunityOpen } from '../../api/admin.js';
import { fetchSectors } from '../../api/catalog.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import Pagination from '../../components/admin/Pagination.jsx';
import SearchBox from '../../components/admin/SearchBox.jsx';
import useAdminList from '../../components/admin/useAdminList.js';
import ConfirmDialog from '../../components/ui/ConfirmDialog.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import Toast from '../../components/ui/Toast.jsx';
import { formatDate } from '../../utils/deadline.js';

export default function AdminOpportunities() {
  const { params, setParam, data, error, reload } = useAdminList(fetchAdminOpportunities);
  const [partners, setPartners] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [pending, setPending] = useState(null);     // {opp, open}
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState('');
  const [toast, setToast] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  useEffect(() => {
    fetchPartners({ per_page: 100 }).then((d) => setPartners(d.items)).catch(() => {});
    fetchSectors().then(setSectors).catch(() => {});
  }, []);

  const confirm = async () => {
    setBusy(true);
    setDialogError('');
    try {
      await setOpportunityOpen(pending.opp.opportunity_id, pending.open);
      setToast(`"${pending.opp.title}" ${pending.open ? 'reopened' : 'closed'}`);
      setPending(null);
      reload();
    } catch (err) {
      setDialogError(parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: 'title', label: 'Opportunity', render: (o) => (
      <><strong>{o.title}</strong><div className="muted small">{o.organization_name}</div></>) },
    { key: 'sector', label: 'Sector' },
    { key: 'status', label: 'Status', render: (o) => <span className={`badge badge--${o.status}`}>{o.status}</span> },
    { key: 'applicants', label: 'Applicants' },
    { key: 'slots', label: 'Slots filled', render: (o) => `${o.slots_filled}/${o.slots}` },
    { key: 'deadline', label: 'Deadline', render: (o) => formatDate(o.application_deadline) },
    { key: 'actions', label: 'Actions', render: (o) => (o.status === 'open' ? (
      <button type="button" className="btn btn--danger btn--sm" onClick={() => { setDialogError(''); setPending({ opp: o, open: false }); }}>Close</button>
    ) : (
      <button type="button" className="btn btn--secondary btn--sm" disabled={!o.can_reopen}
        title={o.can_reopen ? '' : 'The deadline has passed or all slots are filled'}
        onClick={() => { setDialogError(''); setPending({ opp: o, open: true }); }}>Reopen</button>
    )) },
  ];

  return (
    <AdminLayout title="Opportunities">
      <div className="filter-row" role="group" aria-label="Filter opportunities">
        <SearchBox id="opp-search" value={params.search} onSearch={(v) => setParam('search', v)}
          placeholder="Title or company" />
        <div className="field">
          <label htmlFor="opp-partner">Company</label>
          <select id="opp-partner" value={params.partner_id ?? ''} onChange={(e) => setParam('partner_id', e.target.value)}>
            <option value="">All</option>
            {partners.map((p) => <option key={p.partner_id} value={p.partner_id}>{p.organization_name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="opp-sector">Sector</label>
          <select id="opp-sector" value={params.sector_id ?? ''} onChange={(e) => setParam('sector_id', e.target.value)}>
            <option value="">All</option>
            {sectors.map((s) => <option key={s.sector_id} value={s.sector_id}>{s.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="opp-status">Status</label>
          <select id="opp-status" value={params.status ?? ''} onChange={(e) => setParam('status', e.target.value)}>
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={reload} />
      {!data && !error && <LoadingSkeleton variant="lines" count={4} />}
      {data?.items.length === 0 && <EmptyState icon="💼" title="No opportunities found" />}
      {data?.items.length > 0 && (
        <>
          <DataTable caption="Opportunities" columns={columns} rows={data.items} rowKey={(o) => o.opportunity_id} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => setParam('page', p)} />
        </>
      )}

      {pending && (
        <ConfirmDialog title={pending.open ? 'Reopen opportunity?' : 'Close opportunity?'}
          confirmLabel={pending.open ? 'Reopen' : 'Close'} danger={!pending.open} busy={busy}
          error={dialogError} onConfirm={confirm} onCancel={() => setPending(null)}>
          <p>
            {pending.open ? 'Reopen' : 'Close'} <strong>{pending.opp.title}</strong> ({pending.opp.organization_name})?
          </p>
          <p className="muted small">
            {pending.open
              ? 'Students will see it again and it will be included in recommendations.'
              : 'Students will no longer see it or be matched to it. Existing applications are kept.'}
            {' '}The recommendation model is retrained afterwards.
          </p>
        </ConfirmDialog>
      )}
      <Toast message={toast} onDone={clearToast} />
    </AdminLayout>
  );
}
