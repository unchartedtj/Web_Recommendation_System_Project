/**
 * "Post Opportunity" (/partner/opportunities/new) and
 * "Edit Opportunity" (/partner/opportunities/:id/edit): same form, different submit.
 *
 * This page loads the data the form needs (the unit list, plus the existing opportunity
 * when editing), then shows <OpportunityForm> and decides whether saving means
 * "create" or "update".
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { parseApiError } from '../../api/client.js';
import { createOpportunity, fetchMyOpportunity, updateOpportunity } from '../../api/opportunities.js';
import { fetchUnits } from '../../api/units.js';
import DashboardLayout from '../../components/DashboardLayout.jsx';
import OpportunityForm, { toFormState } from '../../components/OpportunityForm.jsx';
import { PARTNER_NAV } from './partnerNav.js';

export default function OpportunityEditor() {
  // useParams reads ":id" from the URL; on the "new" page there is no id.
  const { id } = useParams();
  const isEdit = Boolean(id);   // true on /edit, false on /new
  const navigate = useNavigate();

  const [units, setUnits] = useState(null);                            // null = still loading
  const [initial, setInitial] = useState(isEdit ? null : undefined);   // undefined = blank form
  const [loadError, setLoadError] = useState('');

  // Load everything the form needs, when the page opens (and again if the id changes).
  useEffect(() => {
    const loads = [fetchUnits().then(setUnits)];
    if (isEdit) loads.push(fetchMyOpportunity(id).then((o) => setInitial(toFormState(o))));
    // Promise.all waits for all loads; if any fails, show its message.
    Promise.all(loads).catch((err) => setLoadError(parseApiError(err).message));
  }, [id, isEdit]);

  // What "submit" means: update when editing, create otherwise.
  const handleSubmit = async (payload) => {
    try {
      const saved = isEdit ? await updateOpportunity(id, payload) : await createOpportunity(payload);
      // Back to the list, with a success message for it to show.
      navigate('/partner', {
        state: { message: `"${saved.title}" ${isEdit ? 'updated' : 'posted'} successfully.` },
      });
    } catch (err) {
      throw parseApiError(err); // OpportunityForm shows the field errors
    }
  };

  // Only show the form once the units (and, when editing, the opportunity) have loaded.
  const ready = units !== null && initial !== null;

  return (
    <DashboardLayout title={isEdit ? 'Edit opportunity' : 'Post opportunity'} nav={PARTNER_NAV}>
      {loadError && <div className="alert alert--error">{loadError}</div>}
      {!ready && !loadError && <p className="muted">Loading…</p>}
      {ready && (
        <OpportunityForm
          // A different key makes React build a fresh form (e.g. switching from edit to new).
          key={id ?? 'new'}
          units={units}
          initial={initial}
          submitLabel={isEdit ? 'Save changes' : 'Post opportunity'}
          onSubmit={handleSubmit}
          onCancel={() => navigate('/partner')}
        />
      )}
    </DashboardLayout>
  );
}
