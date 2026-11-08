/**
 * Marks verification (/admin/verifications): students who uploaded a transcript, pending first.
 * Opening one shows the marks the student typed next to their transcript PDF, with
 * Accept and Reject (a reason is required to reject). Accepted students can apply.
 */
import { useCallback, useEffect, useState } from 'react';
import { fetchTranscript, fetchTranscriptFileUrl, fetchTranscripts, reviewTranscript } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import Pagination from '../../components/admin/Pagination.jsx';
import SearchBox from '../../components/admin/SearchBox.jsx';
import useAdminList from '../../components/admin/useAdminList.js';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import Modal from '../../components/ui/Modal.jsx';
import Toast from '../../components/ui/Toast.jsx';
import { formatDate } from '../../utils/deadline.js';

const LABELS = { pending: 'Pending', accepted: 'Accepted', rejected: 'Rejected' };

export function VerifyStatus({ status }) {
  return <span className={`verify-status verify-status--${status}`}>{LABELS[status] ?? status}</span>;
}

function ReviewPanel({ id, onClose, onDone }) {
  const [t, setT] = useState(null);
  const [pdfUrl, setPdfUrl] = useState('');
  const [error, setError] = useState('');
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let url = '';
    fetchTranscript(id).then(setT).catch((err) => setError(parseApiError(err).message));
    fetchTranscriptFileUrl(id)
      .then((u) => { url = u; setPdfUrl(u); })
      .catch((err) => setError(parseApiError(err).message));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [id]);

  const decide = async (action) => {
    if (action === 'reject' && !reason.trim()) {
      setError('Give the student a reason for the rejection.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await reviewTranscript(id, action === 'reject' ? { action, reason: reason.trim() } : { action });
      onDone(action === 'accept' ? 'Marks accepted: the student can now apply' : 'Marks rejected');
    } catch (err) {
      setError(parseApiError(err).message);
      setBusy(false);
    }
  };

  return (
    <Modal title={t ? `Verify marks: ${t.student.name}` : 'Verify marks'} onClose={onClose} footer={(
      <>
        <button type="button" className="btn btn--secondary" onClick={onClose} disabled={busy}>Close</button>
        {t && !rejecting && (
          <>
            <button type="button" className="btn btn--danger" onClick={() => setRejecting(true)} disabled={busy}>Reject</button>
            <button type="button" className="btn btn--primary" onClick={() => decide('accept')} disabled={busy}>
              Accept marks
            </button>
          </>
        )}
        {t && rejecting && (
          <button type="button" className="btn btn--danger" onClick={() => decide('reject')} disabled={busy}>
            Confirm rejection
          </button>
        )}
      </>
    )}>
      <ErrorBanner message={error} />
      {!t && !error && <LoadingSkeleton variant="lines" count={4} />}
      {t && (
        <div className="verify-grid">
          <div>
            <p className="small">
              {t.student.admission_no} · {t.student.course}, year {t.student.year_of_study}<br />
              Uploaded {formatDate(t.uploaded_at)} · <VerifyStatus status={t.status} />
            </p>
            <h3 className="small-heading">Marks the student entered</h3>
            <table className="table compact-table">
              <thead><tr><th>Unit</th><th>Mark</th></tr></thead>
              <tbody>
                {t.marks.map((m) => (
                  <tr key={m.unit}><td data-label="Unit">{m.unit}</td><td data-label="Mark">{m.mark}</td></tr>
                ))}
              </tbody>
            </table>
            {rejecting && (
              <div className="field">
                <label htmlFor="reject-reason">Reason (shown to the student)</label>
                <textarea id="reject-reason" rows={3} maxLength={255} value={reason}
                  placeholder="e.g. Your OOP mark is 58 on the transcript, not 65."
                  onChange={(e) => setReason(e.target.value)} />
              </div>
            )}
          </div>
          <div className="verify-grid__pdf">
            <h3 className="small-heading">Transcript</h3>
            {pdfUrl ? (
              <>
                <iframe title="Transcript PDF" src={pdfUrl} className="verify-pdf" />
                <a className="small" href={pdfUrl} target="_blank" rel="noopener noreferrer">Open in a new tab</a>
              </>
            ) : !error && <LoadingSkeleton variant="lines" count={2} />}
          </div>
        </div>
      )}
    </Modal>
  );
}

export default function AdminVerifications() {
  const { params, setParam, data, error, reload } = useAdminList(fetchTranscripts);
  const [open, setOpen] = useState(null);
  const [toast, setToast] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  const columns = [
    { key: 'student', label: 'Student', render: (r) => (
      <><strong>{r.student.name}</strong><div className="muted small">{r.student.admission_no}</div></>) },
    { key: 'course', label: 'Course', render: (r) => `${r.student.course} · Year ${r.student.year_of_study}` },
    { key: 'uploaded', label: 'Uploaded', render: (r) => formatDate(r.uploaded_at) },
    { key: 'status', label: 'Status', render: (r) => <VerifyStatus status={r.status} /> },
    { key: 'actions', label: 'Actions', render: (r) => (
      <button type="button" className="btn btn--primary btn--sm" onClick={() => setOpen(r.transcript_id)}>
        {r.status === 'pending' ? 'Review' : 'View'}
      </button>) },
  ];

  return (
    <AdminLayout title="Marks verification">
      <p className="muted">
        Students upload their transcript and enter their marks. Check that they match, then accept or
        reject. Only students with accepted marks can apply for internships.
        {data && ` ${data.pending} waiting for review.`}
      </p>
      <div className="filter-row" role="group" aria-label="Filter transcripts">
        <SearchBox id="verify-search" value={params.search} onSearch={(v) => setParam('search', v)}
          placeholder="Name or admission no" />
        <div className="field">
          <label htmlFor="verify-status">Status</label>
          <select id="verify-status" value={params.status ?? ''} onChange={(e) => setParam('status', e.target.value)}>
            <option value="">All (pending first)</option>
            {Object.entries(LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={reload} />
      {!data && !error && <LoadingSkeleton variant="lines" count={4} />}
      {data?.items.length === 0 && (
        <EmptyState icon="📄" title="Nothing to verify">
          Transcripts appear here when students upload them on their profile.
        </EmptyState>
      )}
      {data?.items.length > 0 && (
        <>
          <DataTable caption="Transcripts" columns={columns} rows={data.items} rowKey={(r) => r.transcript_id} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => setParam('page', p)} />
        </>
      )}

      {open && (
        <ReviewPanel id={open} onClose={() => setOpen(null)}
          onDone={(msg) => { setOpen(null); setToast(msg); reload(); }} />
      )}
      <Toast message={toast} onDone={clearToast} />
    </AdminLayout>
  );
}
