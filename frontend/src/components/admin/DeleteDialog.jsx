/**
 * "Delete … permanently?" confirmation for admins. When `userId` is given, it first looks up
 * what else will be deleted (applications, placements, internships) and lists it.
 *
 *   name       what is being deleted, e.g. "Brian Kamau"
 *   userId     the account's user_id (students, partners, accounts), to fetch the impact
 *   extra      text listing what else goes, when no userId (e.g. an internship's applicants)
 *   onDelete   async () => ...; throw the parsed API error on failure
 */
import { useEffect, useState } from 'react';
import { fetchUserImpact } from '../../api/admin.js';
import ConfirmDialog from '../ui/ConfirmDialog.jsx';

function impactLines(impact) {
  const lines = [];
  if (impact.opportunities) lines.push(`${impact.opportunities} internship${impact.opportunities === 1 ? '' : 's'}`);
  if (impact.applications) lines.push(`${impact.applications} application${impact.applications === 1 ? '' : 's'}`);
  if (impact.placements) lines.push(`${impact.placements} placement record${impact.placements === 1 ? '' : 's'}`);
  return lines;
}

export default function DeleteDialog({ title, name, userId, extra, onDelete, onCancel }) {
  const [impact, setImpact] = useState(userId ? null : {});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!userId) return;
    fetchUserImpact(userId).then(setImpact).catch(() => setImpact({}));
  }, [userId]);

  const run = async () => {
    setBusy(true);
    setError('');
    try {
      await onDelete();
    } catch ({ message }) {
      setError(message);
      setBusy(false);
    }
  };

  const lines = impact ? impactLines(impact) : [];
  return (
    <ConfirmDialog title={title} confirmLabel="Delete permanently" danger busy={busy}
      confirmDisabled={impact === null} error={error} onConfirm={run} onCancel={onCancel}>
      <p>Delete <strong>{name}</strong>? This cannot be undone.</p>
      {impact === null && <p className="muted small">Checking what else will be deleted…</p>}
      {(lines.length > 0 || extra) && (
        <div className="alert alert--warn">
          This will also delete: {lines.length > 0 ? lines.join(', ') : extra}.
        </div>
      )}
      {impact && !lines.length && !extra && <p className="muted small">Nothing else depends on it.</p>}
    </ConfirmDialog>
  );
}
