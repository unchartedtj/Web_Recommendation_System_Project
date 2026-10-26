/**
 * Catalog (/admin/catalog): three tabs, Skills, Sectors and Units. Add, rename and
 * activate/deactivate, with "in use" counts. Items in use are never deleted, only deactivated.
 *
 * Units are special: every student needs a mark for every active unit, so adding (or
 * re-activating) a unit makes every complete profile incomplete. A strong warning with the
 * number of affected students is shown first.
 */
import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { createCatalogItem, fetchCatalog, updateCatalogItem } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import DataTable from '../../components/admin/DataTable.jsx';
import { ActivePill } from '../../components/admin/Pill.jsx';
import FormField from '../../components/FormField.jsx';
import ConfirmDialog from '../../components/ui/ConfirmDialog.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import Toast from '../../components/ui/Toast.jsx';

const TABS = [
  { kind: 'skills', label: 'Skills', idKey: 'skill_id', listKey: 'skills', singular: 'skill' },
  { kind: 'sectors', label: 'Sectors', idKey: 'sector_id', listKey: 'sectors', singular: 'sector' },
  { kind: 'units', label: 'Units', idKey: 'unit_id', listKey: 'units', singular: 'unit' },
];

export default function AdminCatalog() {
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.kind === params.get('tab')) ?? TABS[0];
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [dialog, setDialog] = useState(null);      // {type: add|rename|toggle, item?}
  const [form, setForm] = useState({ name: '', category: '' });
  const [fieldErrors, setFieldErrors] = useState({});
  const [dialogError, setDialogError] = useState('');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  const load = useCallback(() => {
    setError('');
    setData(null);
    fetchCatalog(tab.kind).then(setData).catch((err) => setError(parseApiError(err).message));
  }, [tab.kind]);
  useEffect(load, [load]);

  const items = data?.[tab.listKey] ?? [];
  const affected = data?.students_with_complete_profile ?? 0;
  // Adding or re-activating a UNIT needs the strong warning.
  const needsUnitWarning = tab.kind === 'units' && dialog
    && (dialog.type === 'add' || (dialog.type === 'toggle' && !dialog.item.is_active));

  const openDialog = (type, item = null) => {
    setForm({ name: item?.name ?? '', category: item?.category ?? '' });
    setFieldErrors({});
    setDialogError('');
    setDialog({ type, item });
  };

  const run = async () => {
    const { type, item } = dialog;
    const confirm = needsUnitWarning ? { confirm: true } : {};
    setBusy(true);
    setDialogError('');
    try {
      if (type === 'add') {
        await createCatalogItem(tab.kind, {
          name: form.name, ...(tab.kind === 'skills' ? { category: form.category } : {}), ...confirm });
        setToast(`${tab.singular} "${form.name}" added`);
      } else if (type === 'rename') {
        await updateCatalogItem(tab.kind, item[tab.idKey], {
          name: form.name, ...(tab.kind === 'skills' ? { category: form.category } : {}) });
        setToast(`Renamed to "${form.name}"`);
      } else {
        await updateCatalogItem(tab.kind, item[tab.idKey], { is_active: !item.is_active, ...confirm });
        setToast(`"${item.name}" ${item.is_active ? 'deactivated' : 'activated'}`);
      }
      setDialog(null);
      load();
    } catch (err) {
      const { message, fields } = parseApiError(err);
      setDialogError(message);
      setFieldErrors(fields);
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: 'name', label: 'Name', render: (i) => <strong>{i.name}</strong> },
    ...(tab.kind === 'skills' ? [{ key: 'category', label: 'Category' }] : []),
    { key: 'in_use', label: 'In use', render: (i) => (i.in_use ? `${i.in_use}×` : 'Not used') },
    { key: 'status', label: 'Status', render: (i) => <ActivePill active={i.is_active} /> },
    { key: 'actions', label: 'Actions', render: (i) => (
      <div className="row-actions">
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => openDialog('rename', i)}>Rename</button>
        <button type="button" className={`btn btn--sm ${i.is_active ? 'btn--danger' : 'btn--secondary'}`}
          onClick={() => openDialog('toggle', i)}>{i.is_active ? 'Deactivate' : 'Activate'}</button>
      </div>) },
  ];

  const dialogTitle = dialog && {
    add: `Add a ${tab.singular}`, rename: `Rename ${tab.singular}`,
    toggle: dialog.item ? `${dialog.item.is_active ? 'Deactivate' : 'Activate'} "${dialog.item.name}"?` : '',
  }[dialog.type];

  return (
    <AdminLayout title="Catalog" actions={(
      <button type="button" className="btn btn--primary" onClick={() => openDialog('add')}>+ Add {tab.singular}</button>
    )}>
      <div className="tabs" role="tablist" aria-label="Catalogue">
        {TABS.map((t) => (
          <button key={t.kind} type="button" role="tab" aria-selected={t.kind === tab.kind}
            className={`tab${t.kind === tab.kind ? ' tab--active' : ''}`}
            onClick={() => setParams({ tab: t.kind })}>{t.label}</button>
        ))}
      </div>
      <p className="muted small">
        Items that are in use (by opportunities, students or grades) are never deleted, only
        deactivated. Every change retrains the recommendation model.
      </p>

      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && <LoadingSkeleton variant="lines" count={5} />}
      {data && <DataTable caption={tab.label} columns={columns} rows={items} rowKey={(i) => i[tab.idKey]} />}

      {dialog && (
        <ConfirmDialog title={dialogTitle} busy={busy} error={dialogError}
          danger={needsUnitWarning || (dialog.type === 'toggle' && dialog.item.is_active)}
          confirmLabel={needsUnitWarning ? 'I understand, continue' : 'Save'}
          confirmDisabled={dialog.type !== 'toggle' && !form.name.trim()}
          onConfirm={run} onCancel={() => setDialog(null)}>
          {needsUnitWarning && (
            <div className="alert alert--error" role="alert">
              <strong>Warning:</strong> every student must have a mark for every active unit.
              {' '}This makes <strong>{affected}</strong> complete student {affected === 1 ? 'profile' : 'profiles'}
              {' '}incomplete until each student enters a mark for this unit, and they won&apos;t get
              recommendations until then.
            </div>
          )}
          {dialog.type === 'toggle' && dialog.item.is_active && (
            <p>It will no longer be offered on forms{dialog.item.in_use ? ', but existing data that uses it is kept' : ''}.</p>
          )}
          {dialog.type !== 'toggle' && (
            <>
              <FormField label="Name" name="catalog-name" value={form.name} error={fieldErrors.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} />
              {tab.kind === 'skills' && (
                <FormField label="Category" name="catalog-category" value={form.category}
                  error={fieldErrors.category} placeholder="e.g. Programming"
                  onChange={(e) => setForm({ ...form, category: e.target.value })} />
              )}
            </>
          )}
        </ConfirmDialog>
      )}
      <Toast message={toast} onDone={clearToast} />
    </AdminLayout>
  );
}
