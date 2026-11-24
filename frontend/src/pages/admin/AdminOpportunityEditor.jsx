/**
 * Add or edit an internship as the admin (/admin/internships/opportunities/new and …/:id/edit).
 * Reuses the partner's OpportunityForm (units + minimum marks, skills, sector, county), with a
 * "Company" choice on top when adding. The same validation as for partners applies.
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { createAdminOpportunity, fetchAdminOpportunity, fetchPartners, updateAdminOpportunity } from '../../api/admin.js';
import { fetchCounties, fetchSectors, fetchSkillCategories, fetchUnits } from '../../api/catalog.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import OpportunityForm, { toFormState } from '../../components/OpportunityForm.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';

const LIST = '/admin/internships/opportunities';

export default function AdminOpportunityEditor() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [lists, setLists] = useState(null);           // units, sectors, skills, counties, partners
  const [initial, setInitial] = useState(isEdit ? null : undefined);
  const [company, setCompany] = useState(null);       // the opportunity's company when editing
  const [partnerId, setPartnerId] = useState('');
  const [partnerError, setPartnerError] = useState('');
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    Promise.all([fetchUnits(), fetchSectors(), fetchSkillCategories(), fetchCounties(),
      fetchPartners({ per_page: 100 })])
      .then(([units, sectors, skillCategories, counties, partners]) =>
        setLists({ units, sectors, skillCategories, counties, partners: partners.items }))
      .catch((err) => setLoadError(parseApiError(err).message));
    if (isEdit) {
      fetchAdminOpportunity(id)
        .then((o) => { setInitial(toFormState(o)); setCompany(o.organization_name); })
        .catch((err) => setLoadError(parseApiError(err).message));
    }
  }, [id, isEdit]);

  const submit = async (payload) => {
    if (!isEdit && !partnerId) {
      setPartnerError('Choose the company offering this internship');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      throw { message: 'Choose the company offering this internship', fields: {} };   // eslint-disable-line no-throw-literal
    }
    try {
      const saved = isEdit
        ? await updateAdminOpportunity(id, payload)
        : await createAdminOpportunity({ ...payload, partner_id: Number(partnerId) });
      navigate(LIST, { state: { message: `"${saved.title}" ${isEdit ? 'updated' : 'posted'}` } });
    } catch (err) {
      throw parseApiError(err);
    }
  };

  const ready = lists && initial !== null;
  return (
    <AdminLayout title={isEdit ? 'Edit internship' : 'Add internship'}>
      <ErrorBanner message={loadError} />
      {!ready && !loadError && <LoadingSkeleton variant="cards" count={1} />}
      {ready && (
        <>
          <div className="panel company-choice">
            {isEdit ? (
              <p><span className="muted">Company:</span> <strong>{company}</strong></p>
            ) : (
              <div className={`field ${partnerError ? 'field--invalid' : ''}`}>
                <label htmlFor="admin-opp-partner">Company offering this internship</label>
                <select id="admin-opp-partner" value={partnerId}
                  onChange={(e) => { setPartnerId(e.target.value); setPartnerError(''); }}>
                  <option value="">Select a company…</option>
                  {lists.partners.map((p) => (
                    <option key={p.partner_id} value={p.partner_id}>{p.organization_name}</option>
                  ))}
                </select>
                {partnerError && <p className="field__error">{partnerError}</p>}
              </div>
            )}
          </div>
          <OpportunityForm key={id ?? 'new'} units={lists.units} sectors={lists.sectors}
            counties={lists.counties} skillCategories={lists.skillCategories} initial={initial}
            submitLabel={isEdit ? 'Save changes' : 'Post internship'} onSubmit={submit}
            onCancel={() => navigate(LIST)} />
        </>
      )}
    </AdminLayout>
  );
}
