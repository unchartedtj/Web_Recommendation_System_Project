/**
 * Students (/admin/students): searchable list (name or admission no) with filters for year,
 * profile complete and placement status. Clicking a student opens their read-only record.
 */
import { useNavigate } from 'react-router-dom';
import { fetchStudents } from '../../api/admin.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import Pagination from '../../components/admin/Pagination.jsx';
import { ActivePill, PLACEMENT_LABELS, PlacementStatusPill } from '../../components/admin/Pill.jsx';
import SearchBox from '../../components/admin/SearchBox.jsx';
import useAdminList from '../../components/admin/useAdminList.js';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';

export default function AdminStudents() {
  const navigate = useNavigate();
  const { params, setParam, data, error, reload } = useAdminList(fetchStudents);

  const columns = [
    { key: 'name', label: 'Student', render: (r) => (
      <><strong>{r.name}</strong><div className="muted small">{r.email}</div></>) },
    { key: 'admission_no', label: 'Admission no' },
    { key: 'course', label: 'Course', render: (r) => `${r.course} · Year ${r.year_of_study}` },
    { key: 'profile', label: 'Profile', render: (r) => (r.profile_complete
      ? <span className="status status--ok"><span aria-hidden="true">✓</span> Complete</span>
      : <span className="status status--warn"><span aria-hidden="true">⚠</span> Incomplete</span>) },
    { key: 'applications', label: 'Applications' },
    { key: 'placement', label: 'Placement', render: (r) => (r.placement_status
      ? <PlacementStatusPill status={r.placement_status} /> : <span className="muted">None</span>) },
    { key: 'active', label: 'Account', render: (r) => <ActivePill active={r.is_active} /> },
  ];

  return (
    <AdminLayout title="Students">
      <div className="filter-row" role="group" aria-label="Filter students">
        <SearchBox id="student-search" value={params.search} onSearch={(v) => setParam('search', v)}
          placeholder="Name or admission no" />
        <div className="field">
          <label htmlFor="student-year">Year</label>
          <select id="student-year" value={params.year ?? ''} onChange={(e) => setParam('year', e.target.value)}>
            <option value="">All</option>
            {[1, 2, 3, 4].map((y) => <option key={y} value={y}>Year {y}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="student-complete">Profile</label>
          <select id="student-complete" value={params.profile_complete ?? ''}
            onChange={(e) => setParam('profile_complete', e.target.value)}>
            <option value="">All</option>
            <option value="true">Complete</option>
            <option value="false">Incomplete</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="student-placement">Placement</label>
          <select id="student-placement" value={params.placement_status ?? ''}
            onChange={(e) => setParam('placement_status', e.target.value)}>
            <option value="">All</option>
            <option value="none">No placement</option>
            {Object.entries(PLACEMENT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={reload} />
      {!data && !error && <LoadingSkeleton variant="lines" count={4} />}
      {data?.items.length === 0 && <EmptyState icon="🧑‍🎓" title="No students found" />}
      {data?.items.length > 0 && (
        <>
          <DataTable caption="Students" columns={columns} rows={data.items} rowKey={(r) => r.student_id}
            onRowClick={(r) => navigate(`/admin/students/${r.student_id}`)} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => setParam('page', p)} />
        </>
      )}
    </AdminLayout>
  );
}
