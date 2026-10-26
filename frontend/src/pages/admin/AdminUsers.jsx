/**
 * User accounts (/admin/users): role filter and search, Activate / Deactivate (the dialog
 * first shows what will happen, e.g. "This will close 2 open opportunities"), Reset password
 * (the temporary password is shown once) and Create admin.
 */
import { useCallback, useState } from 'react';
import { createAdmin, fetchUserImpact, fetchUsers, resetUserPassword, setUserActive } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import { formatDateTime } from '../../components/admin/ActivityList.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import Pagination from '../../components/admin/Pagination.jsx';
import { ActivePill } from '../../components/admin/Pill.jsx';
import SearchBox from '../../components/admin/SearchBox.jsx';
import useAdminList from '../../components/admin/useAdminList.js';
import FormField from '../../components/FormField.jsx';
import ConfirmDialog from '../../components/ui/ConfirmDialog.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import Toast from '../../components/ui/Toast.jsx';
import { useAuth } from '../../context/AuthContext.jsx';

const ROLE_LABELS = { student: 'Student', industry_partner: 'Industry partner', system_admin: 'System admin' };

function impactText(user, impact) {
  if (!impact) return 'Checking what this will change…';
  const parts = [];
  if (user.role === 'industry_partner') {
    parts.push(impact.open_opportunities
      ? `This will close ${impact.open_opportunities} open ${impact.open_opportunities === 1 ? 'opportunity' : 'opportunities'} and retrain the model.`
      : 'They have no open opportunities.');
  }
  if (user.role === 'student') {
    parts.push(impact.active_applications
      ? `This will withdraw ${impact.active_applications} pending or shortlisted ${impact.active_applications === 1 ? 'application' : 'applications'}.`
      : 'They have no active applications.');
  }
  return parts.join(' ');
}

export default function AdminUsers() {
  const { user: me } = useAuth();
  const { params, setParam, data, error, reload } = useAdminList(fetchUsers);
  const [dialog, setDialog] = useState(null);          // {type, user, impact?}
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState('');
  const [tempPassword, setTempPassword] = useState(null);   // {email, password}: shown once
  const [newAdmin, setNewAdmin] = useState({ name: '', email: '', password: '' });
  const [adminErrors, setAdminErrors] = useState({});
  const [toast, setToast] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  const open = (type, user) => {
    setDialogError('');
    setDialog({ type, user, impact: null });
    if (type === 'deactivate') {
      fetchUserImpact(user.user_id)
        .then((impact) => setDialog((d) => (d && d.user.user_id === user.user_id ? { ...d, impact } : d)))
        .catch(() => setDialog((d) => (d ? { ...d, impact: { open_opportunities: 0, active_applications: 0 } } : d)));
    }
  };

  const run = async () => {
    const { type, user } = dialog;
    setBusy(true);
    setDialogError('');
    try {
      if (type === 'deactivate' || type === 'activate') {
        const res = await setUserActive(user.user_id, type === 'activate');
        const extra = type === 'deactivate'
          ? ` (${res.closed_opportunities} opportunities closed, ${res.withdrawn_applications} applications withdrawn)` : '';
        setToast(`${user.email} ${type === 'activate' ? 'activated' : 'deactivated'}${extra}`);
      } else if (type === 'reset') {
        const res = await resetUserPassword(user.user_id);
        setTempPassword({ email: user.email, password: res.temporary_password });
      } else if (type === 'create') {
        await createAdmin(newAdmin);
        setToast(`Admin ${newAdmin.email} created`);
        setNewAdmin({ name: '', email: '', password: '' });
      }
      setDialog(null);
      reload();
    } catch (err) {
      const { message, fields } = parseApiError(err);
      setDialogError(message);
      if (type === 'create') setAdminErrors(fields);
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: 'email', label: 'Account', render: (u) => (
      <><strong>{u.name}</strong><div className="muted small">{u.email}</div></>) },
    { key: 'role', label: 'Role', render: (u) => ROLE_LABELS[u.role] ?? u.role },
    { key: 'active', label: 'Status', render: (u) => (
      <>
        <ActivePill active={u.is_active} />
        {u.must_change_password && <div className="muted small">Must change password</div>}
      </>) },
    { key: 'last_login', label: 'Last login', render: (u) => formatDateTime(u.last_login_at) },
    { key: 'actions', label: 'Actions', render: (u) => (
      <div className="row-actions">
        {u.is_active ? (
          <button type="button" className="btn btn--danger btn--sm" disabled={u.user_id === me?.user_id}
            title={u.user_id === me?.user_id ? "You can't deactivate your own account" : ''}
            onClick={() => open('deactivate', u)}>Deactivate</button>
        ) : (
          <button type="button" className="btn btn--secondary btn--sm" onClick={() => open('activate', u)}>Activate</button>
        )}
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => open('reset', u)}>Reset password</button>
      </div>) },
  ];

  const titles = {
    deactivate: 'Deactivate account?', activate: 'Activate account?',
    reset: 'Reset password?', create: 'Create a system admin',
  };

  return (
    <AdminLayout title="Users" actions={(
      <button type="button" className="btn btn--primary" onClick={() => { setAdminErrors({}); open('create', null); }}>
        + Create admin
      </button>
    )}>
      <div className="filter-row" role="group" aria-label="Filter users">
        <SearchBox id="user-search" label="Search by email" value={params.search}
          onSearch={(v) => setParam('search', v)} />
        <div className="field">
          <label htmlFor="user-role">Role</label>
          <select id="user-role" value={params.role ?? ''} onChange={(e) => setParam('role', e.target.value)}>
            <option value="">All roles</option>
            {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="user-active">Status</label>
          <select id="user-active" value={params.active ?? ''} onChange={(e) => setParam('active', e.target.value)}>
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Deactivated</option>
          </select>
        </div>
      </div>

      {tempPassword && (
        <div className="alert alert--warn temp-password" role="status">
          <p><strong>Temporary password for {tempPassword.email}:</strong></p>
          <p className="temp-password__value"><code>{tempPassword.password}</code>
            <button type="button" className="btn btn--secondary btn--sm"
              onClick={() => navigator.clipboard?.writeText(tempPassword.password)}>Copy</button>
          </p>
          <p className="small">Give it to the user now: it won&apos;t be shown again. They must choose a
            new password the next time they log in.</p>
          <button type="button" className="btn btn--secondary btn--sm" onClick={() => setTempPassword(null)}>Done</button>
        </div>
      )}

      <ErrorBanner message={error} onRetry={reload} />
      {!data && !error && <LoadingSkeleton variant="lines" count={4} />}
      {data?.items.length === 0 && <EmptyState icon="👥" title="No users found" />}
      {data?.items.length > 0 && (
        <>
          <DataTable caption="User accounts" columns={columns} rows={data.items} rowKey={(u) => u.user_id} />
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => setParam('page', p)} />
        </>
      )}

      {dialog && (
        <ConfirmDialog title={titles[dialog.type]} busy={busy} error={dialogError}
          danger={dialog.type === 'deactivate'}
          confirmLabel={{ deactivate: 'Deactivate', activate: 'Activate', reset: 'Reset password', create: 'Create admin' }[dialog.type]}
          confirmDisabled={dialog.type === 'deactivate' && !dialog.impact}
          onConfirm={run} onCancel={() => setDialog(null)}>
          {dialog.type === 'deactivate' && (
            <>
              <p>Deactivate <strong>{dialog.user.email}</strong>? They won&apos;t be able to log in, and
                anyone using the account is signed out.</p>
              <p className="alert alert--warn">{impactText(dialog.user, dialog.impact)}</p>
            </>
          )}
          {dialog.type === 'activate' && <p>Allow <strong>{dialog.user.email}</strong> to log in again?</p>}
          {dialog.type === 'reset' && (
            <p>A new temporary password will be created for <strong>{dialog.user.email}</strong>. Their current
              password stops working, and they must choose a new one when they next log in.</p>
          )}
          {dialog.type === 'create' && (
            <>
              <FormField label="Name" name="admin-name" value={newAdmin.name} error={adminErrors.name}
                onChange={(e) => setNewAdmin({ ...newAdmin, name: e.target.value })} />
              <FormField label="Email" name="admin-email" type="email" value={newAdmin.email} error={adminErrors.email}
                onChange={(e) => setNewAdmin({ ...newAdmin, email: e.target.value })} />
              <FormField label="Password" name="admin-password" type="password" autoComplete="new-password"
                placeholder="At least 8 characters, with a letter and a number"
                value={newAdmin.password} error={adminErrors.password}
                onChange={(e) => setNewAdmin({ ...newAdmin, password: e.target.value })} />
            </>
          )}
        </ConfirmDialog>
      )}
      <Toast message={toast} onDone={clearToast} />
    </AdminLayout>
  );
}
