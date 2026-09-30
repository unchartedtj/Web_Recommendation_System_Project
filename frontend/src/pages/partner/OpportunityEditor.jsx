import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { parseApiError } from '../../api/client.js';
import { createOpportunity, fetchMyOpportunity, updateOpportunity } from '../../api/opportunities.js';
import { fetchUnits } from '../../api/units.js';
import DashboardLayout from '../../components/DashboardLayout.jsx';
import OpportunityForm, { toFormState } from '../../components/OpportunityForm.jsx';
import { PARTNER_NAV } from './partnerNav.js';

/**
 * "Post Opportunity" (/partner/opportunities/new) and
 * "Edit Opportunity" (/partner/opportunities/:id/edit): same form, different submit.
 */
export default function OpportunityEditor() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [units, setUnits] = useState(null);
  const [initial, setInitial] = useState(isEdit ? null : undefined); // undefined = blank form
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    const loads = [fetchUnits().then(setUnits)];
    if (isEdit) loads.push(fetchMyOpportunity(id).then((o) => setInitial(toFormState(o))));
    Promise.all(loads).catch((err) => setLoadError(parseApiError(err).message));
  }, [id, isEdit]);

  const handleSubmit = async (payload) => {
    try {
      const saved = isEdit ? await updateOpportunity(id, payload) : await createOpportunity(payload);
      navigate('/partner', {
        state: { message: `"${saved.title}" ${isEdit ? 'updated' : 'posted'} successfully.` },
      });
    } catch (err) {
      throw parseApiError(err); // OpportunityForm shows the field errors
    }
  };

  const ready = units !== null && initial !== null;

  return (
    <DashboardLayout title={isEdit ? 'Edit opportunity' : 'Post opportunity'} nav={PARTNER_NAV}>
      {loadError && <div className="alert alert--error">{loadError}</div>}
      {!ready && !loadError && <p className="muted">Loading…</p>}
      {ready && (
        <OpportunityForm
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
