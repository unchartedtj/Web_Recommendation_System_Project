/**
 * Industry partners (/admin/partners) and one partner's record (/admin/partners/:id).
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { fetchPartner, fetchPartners } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import Pagination from '../../components/admin/Pagination.jsx';
import { ActivePill } from '../../components/admin/Pill.jsx';
import SearchBox from '../../components/admin/SearchBox.jsx';
import useAdminList from '../../components/admin/useAdminList.js';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import { formatDate } from '../../utils/deadline.js';

export function AdminPartners() {
  const navigate = useNavigate();
  const { params, setParam, data, error, reload } = useAdminList(fetchPartners);
  const columns = [
    { key: 'organization_name', label: 'Organisation', render: (r) => (
      <><strong>{r.organization_name}</strong><div className="muted small">{r.email}</div></>) },
    { key: 'contact_person', label: 'Contact' },
    { key: 'phone', label: 'Phone' },
    { key: 'opportunities', label: 'Opportunities', render: (r) => `${r.opportunities} (${r.open_opportunities} open)` },
    { key: 'placements', label: 'Placements' },
    { key: 'active', label: 'Account', render: (r) => <ActivePill active={r.is_active} /> },
  ];
  return (
    <AdminLayout title="Industry partners">
      <div className="filter-row" role="group" aria-label="Filter partners">
        <SearchBox id="partner-search" value={params.search} onSearch={(v) => setParam('search', v)}
          placeholder="Organisation, contact or email" />
      </div>
      <ErrorBanner message={error} onRetry={reload} />
      {!data && !error && <LoadingSkeleton variant="lines" count={4} />}
      {data?.items.length === 0 && <EmptyState icon="🏢" title="No partners found" />}
      {data?.items.length > 0 && (
        <>
          <DataTable caption="Industry partners" columns={columns} rows={data.items} rowKey={(r) => r.partner_id}
            onRowClick={(r) => navigate(`/admin/partners/${r.partner_id}`)} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => setParam('page', p)} />
        </>
      )}
    </AdminLayout>
  );
}

export function AdminPartnerDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    fetchPartner(id).then(setP).catch((err) => setError(parseApiError(err).message));
  }, [id]);
  useEffect(load, [load]);

  const columns = [
    { key: 'title', label: 'Opportunity', render: (o) => <strong>{o.title}</strong> },
    { key: 'status', label: 'Status', render: (o) => <span className={`badge badge--${o.status}`}>{o.status}</span> },
    { key: 'sector', label: 'Sector' },
    { key: 'applicants', label: 'Applicants', render: (o) =>
      `${o.applicants} (${o.application_counts.pending} pending, ${o.application_counts.shortlisted} shortlisted)` },
    { key: 'slots', label: 'Slots filled', render: (o) => `${o.slots_filled}/${o.slots}` },
    { key: 'deadline', label: 'Deadline', render: (o) => formatDate(o.application_deadline) },
  ];
  return (
    <AdminLayout title={p ? p.organization_name : 'Partner'}>
      <Link className="btn btn--secondary btn--sm back-btn" to="/admin/partners">← All partners</Link>
      <ErrorBanner message={error} onRetry={load} />
      {!p && !error && <LoadingSkeleton variant="cards" count={2} />}
      {p && (
        <>
          <section className="panel">
            <dl className="detail-list detail-list--row">
              <div><dt>Contact</dt><dd>{p.contact_person}</dd></div>
              <div><dt>Email</dt><dd>{p.email}</dd></div>
              <div><dt>Phone</dt><dd>{p.phone}</dd></div>
              <div><dt>Account</dt><dd><ActivePill active={p.is_active} /></dd></div>
              <div><dt>Placements</dt><dd>{p.placements}</dd></div>
            </dl>
          </section>
          <h2 className="section-title">Opportunities</h2>
          {p.opportunity_list.length === 0
            ? <EmptyState icon="💼" title="No opportunities posted yet" />
            : <DataTable caption="Opportunities" columns={columns} rows={p.opportunity_list} rowKey={(o) => o.opportunity_id} />}
        </>
      )}
    </AdminLayout>
  );
}
