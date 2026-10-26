/**
 * Activity Log (/admin/activity): who did what and when, filterable and paginated.
 */
import { fetchActivity } from '../../api/admin.js';
import { describeAction, detailsText, formatDateTime } from '../../components/admin/ActivityList.jsx';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import Pagination from '../../components/admin/Pagination.jsx';
import useAdminList from '../../components/admin/useAdminList.js';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';

const AREAS = ['auth', 'opportunity', 'application', 'placement', 'user', 'catalog', 'model', 'sus'];

export default function AdminActivity() {
  const { params, setParam, data, error, reload } = useAdminList(fetchActivity);
  const columns = [
    { key: 'when', label: 'When', render: (a) => formatDateTime(a.created_at) },
    { key: 'action', label: 'Action', render: (a) => <strong>{describeAction(a.action)}</strong> },
    { key: 'actor', label: 'By', render: (a) => (a.actor
      ? <>{a.actor.email}<div className="muted small">{a.actor.role.replace('_', ' ')}</div></>
      : <span className="muted">System</span>) },
    { key: 'target', label: 'Target', render: (a) => (a.target_type ? `${a.target_type} #${a.target_id}` : '—') },
    { key: 'details', label: 'Details', render: (a) => <span className="small">{detailsText(a.details) || '—'}</span> },
  ];
  return (
    <AdminLayout title="Activity log">
      <div className="filter-row" role="group" aria-label="Filter activity">
        <div className="field">
          <label htmlFor="activity-area">Area</label>
          <select id="activity-area" value={(params.action ?? '').split('.')[0]}
            onChange={(e) => setParam('action', e.target.value)}>
            <option value="">Everything</option>
            {AREAS.map((a) => <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="activity-action">Exact action</label>
          <select id="activity-action" value={params.action?.includes('.') ? params.action : ''}
            onChange={(e) => setParam('action', e.target.value)}>
            <option value="">Any</option>
            {(data?.actions ?? []).map((a) => <option key={a} value={a}>{describeAction(a)}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="activity-from">From</label>
          <input id="activity-from" type="date" value={params.from ?? ''} onChange={(e) => setParam('from', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="activity-to">To</label>
          <input id="activity-to" type="date" value={params.to ?? ''} onChange={(e) => setParam('to', e.target.value)} />
        </div>
      </div>
      <ErrorBanner message={error} onRetry={reload} />
      {!data && !error && <LoadingSkeleton variant="lines" count={6} />}
      {data?.items.length === 0 && <EmptyState icon="🕑" title="No activity found" />}
      {data?.items.length > 0 && (
        <>
          <DataTable caption="Activity log" columns={columns} rows={data.items} rowKey={(a) => a.log_id} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => setParam('page', p)} />
        </>
      )}
    </AdminLayout>
  );
}
