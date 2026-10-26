/**
 * Placements (/admin/placements), test case TC09: every placement record with filters,
 * a detail panel (including the student's match when they applied), an edit dialog for the
 * status and dates, and an Export CSV button.
 */
import { useCallback, useEffect, useState } from 'react';
import { downloadCsv, fetchPartners, fetchPlacement, fetchPlacements, updatePlacement } from '../../api/admin.js';
import { fetchSectors } from '../../api/catalog.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import Pagination from '../../components/admin/Pagination.jsx';
import PlacementEditDialog from '../../components/admin/PlacementEditDialog.jsx';
import { PLACEMENT_LABELS, PlacementStatusPill } from '../../components/admin/Pill.jsx';
import SearchBox from '../../components/admin/SearchBox.jsx';
import useAdminList from '../../components/admin/useAdminList.js';
import UnitComparisonTable from '../../components/student/UnitComparisonTable.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import Modal from '../../components/ui/Modal.jsx';
import ScoreBreakdown from '../../components/ui/ScoreBreakdown.jsx';
import Toast from '../../components/ui/Toast.jsx';
import { formatDate } from '../../utils/deadline.js';

function PlacementDetail({ id, onClose, onEdit }) {
  const [p, setP] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    fetchPlacement(id).then(setP).catch((err) => setError(parseApiError(err).message));
  }, [id]);
  const snap = p?.application?.snapshot;
  return (
    <Modal title="Placement details" onClose={onClose} footer={(
      <>
        <button type="button" className="btn btn--secondary" onClick={onClose}>Close</button>
        {p && p.allowed_next.length > 0 && (
          <button type="button" className="btn btn--primary" onClick={() => onEdit(p)}>Edit</button>
        )}
      </>
    )}>
      <ErrorBanner message={error} />
      {!p && !error && <LoadingSkeleton variant="lines" count={3} />}
      {p && (
        <div className="detail-grid">
          <dl className="detail-list">
            <div><dt>Student</dt><dd>{p.student.name} ({p.student.admission_no})</dd></div>
            <div><dt>Email</dt><dd>{p.student_email}</dd></div>
            <div><dt>Company</dt><dd>{p.company.name}</dd></div>
            <div><dt>Internship</dt><dd>{p.opportunity.title}</dd></div>
            <div><dt>Status</dt><dd><PlacementStatusPill status={p.status} /></dd></div>
            <div><dt>Dates</dt><dd>{formatDate(p.start_date)} to {formatDate(p.end_date)}</dd></div>
            {p.status_reason && <div><dt>Reason</dt><dd>{p.status_reason}</dd></div>}
            <div><dt>Match when applied</dt><dd>{p.match_percent_at_apply != null ? `${Math.round(p.match_percent_at_apply)}%` : '—'}</dd></div>
          </dl>
          {snap && (
            <div>
              <h3 className="small-heading">Snapshot when they applied</h3>
              <ScoreBreakdown breakdown={snap.breakdown} />
              <UnitComparisonTable units={snap.units ?? []} mineLabel="Their mark" />
              {p.application.motivation_note && (
                <p className="small"><span className="muted">Note:</span> {p.application.motivation_note}</p>
              )}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

export default function AdminPlacements() {
  const { params, setParam, data, error, reload } = useAdminList(fetchPlacements);
  const [partners, setPartners] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [viewing, setViewing] = useState(null);
  const [editing, setEditing] = useState(null);
  const [toast, setToast] = useState('');
  const [exportError, setExportError] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  useEffect(() => {
    fetchPartners({ per_page: 100 }).then((d) => setPartners(d.items)).catch(() => {});
    fetchSectors().then(setSectors).catch(() => {});
  }, []);

  const save = async (body) => {
    try {
      await updatePlacement(editing.placement_id, body);
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
    setEditing(null);
    setViewing(null);
    setToast('Placement updated');
    reload();
  };

  const exportCsv = () => {
    setExportError('');
    const { page, per_page: _perPage, ...filters } = params;   // export everything that matches
    downloadCsv('/admin/placements/export.csv', 'placements.csv', filters)
      .catch((err) => setExportError(parseApiError(err).message));
  };

  const columns = [
    { key: 'student', label: 'Student', render: (r) => (
      <><strong>{r.student.name}</strong><div className="muted small">{r.student.admission_no}</div></>) },
    { key: 'company', label: 'Company', render: (r) => r.company.name },
    { key: 'internship', label: 'Internship', render: (r) => r.opportunity.title },
    { key: 'status', label: 'Status', render: (r) => <PlacementStatusPill status={r.status} /> },
    { key: 'dates', label: 'Dates', render: (r) => `${formatDate(r.start_date)} – ${formatDate(r.end_date)}` },
    { key: 'match', label: 'Match', render: (r) => (r.match_percent_at_apply != null ? `${Math.round(r.match_percent_at_apply)}%` : '—') },
    { key: 'actions', label: 'Actions', render: (r) => (
      <div className="row-actions">
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => setViewing(r.placement_id)}>View</button>
        {r.allowed_next.length > 0 && (
          <button type="button" className="btn btn--primary btn--sm" onClick={() => setEditing(r)}>Edit</button>
        )}
      </div>) },
  ];

  return (
    <AdminLayout title="Placements" actions={(
      <button type="button" className="btn btn--secondary" onClick={exportCsv}>⬇ Export CSV</button>
    )}>
      <div className="filter-row" role="group" aria-label="Filter placements">
        <SearchBox id="placement-search" value={params.search} onSearch={(v) => setParam('search', v)}
          placeholder="Student, admission no, company…" />
        <div className="field">
          <label htmlFor="placement-status-filter">Status</label>
          <select id="placement-status-filter" value={params.status ?? ''} onChange={(e) => setParam('status', e.target.value)}>
            <option value="">All</option>
            {Object.entries(PLACEMENT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="placement-partner">Company</label>
          <select id="placement-partner" value={params.partner_id ?? ''} onChange={(e) => setParam('partner_id', e.target.value)}>
            <option value="">All</option>
            {partners.map((p) => <option key={p.partner_id} value={p.partner_id}>{p.organization_name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="placement-sector">Sector</label>
          <select id="placement-sector" value={params.sector_id ?? ''} onChange={(e) => setParam('sector_id', e.target.value)}>
            <option value="">All</option>
            {sectors.map((s) => <option key={s.sector_id} value={s.sector_id}>{s.name}</option>)}
          </select>
        </div>
      </div>

      <ErrorBanner message={error || exportError} onRetry={error ? reload : undefined} />
      {!data && !error && <LoadingSkeleton variant="lines" count={4} />}
      {data?.items.length === 0 && (
        <EmptyState icon="🎓" title="No placements found">
          Placements are created when a partner accepts an application.
        </EmptyState>
      )}
      {data?.items.length > 0 && (
        <>
          <DataTable caption="Placement records" columns={columns} rows={data.items} rowKey={(r) => r.placement_id} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => setParam('page', p)} />
        </>
      )}

      {viewing && <PlacementDetail id={viewing} onClose={() => setViewing(null)}
        onEdit={(p) => { setViewing(null); setEditing(p); }} />}
      {editing && <PlacementEditDialog placement={editing} onSave={save} onCancel={() => setEditing(null)} />}
      <Toast message={toast} onDone={clearToast} />
    </AdminLayout>
  );
}
