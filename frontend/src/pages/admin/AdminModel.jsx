/**
 * Model (/admin/model): retrain the recommendation engine, see when it was last trained,
 * the IDF weights it learnt (sortable tables), the 60/25/15 match weights, and the offline
 * evaluation / ablation results.
 */
import { useCallback, useEffect, useState } from 'react';
import { fetchModel, retrainModel } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import { formatDateTime } from '../../components/admin/ActivityList.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';
import Toast from '../../components/ui/Toast.jsx';

function SortableIdf({ title, rows }) {
  const [sort, setSort] = useState({ key: 'idf', desc: true });
  const sorted = [...rows].sort((a, b) => {
    const x = a[sort.key] ?? '';
    const y = b[sort.key] ?? '';
    const cmp = typeof x === 'number' ? x - y : String(x).localeCompare(String(y));
    return sort.desc ? -cmp : cmp;
  });
  const header = (key, label) => (
    <th scope="col" aria-sort={sort.key === key ? (sort.desc ? 'descending' : 'ascending') : 'none'}>
      <button type="button" className="sort-button"
        onClick={() => setSort({ key, desc: sort.key === key ? !sort.desc : key === 'idf' })}>
        {label} {sort.key === key && <span aria-hidden="true">{sort.desc ? '▼' : '▲'}</span>}
      </button>
    </th>
  );
  return (
    <section className="panel">
      <h2 className="small-heading">{title}</h2>
      <p className="muted small">Higher IDF = required by fewer internships = more distinctive.</p>
      <table className="table compact-table">
        <thead><tr>{header('name', 'Name')}{header('idf', 'IDF weight')}</tr></thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.name}><td data-label="Name">{r.name}</td><td data-label="IDF weight">{r.idf.toFixed(4)}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

const CONFIG_LABELS = { grades_only: 'Grades only', grades_skills: 'Grades + skills', all_three: 'Grades + skills + interests' };
const pct = (v) => (v === '' || v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);

export default function AdminModel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState('');
  const clearToast = useCallback(() => setToast(''), []);

  const load = useCallback(() => {
    setError('');
    fetchModel().then(setData).catch((err) => setError(parseApiError(err).message));
  }, []);
  useEffect(load, [load]);

  const retrain = async () => {
    setBusy(true);
    try {
      await retrainModel();
      setToast('Model retrained');
      load();
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const ablation = data?.evaluation?.ablation ?? [];
  const labelled = ablation.filter((r) => r.group !== 'conflicting');
  const conflicting = ablation.filter((r) => r.group === 'conflicting');

  return (
    <AdminLayout title="Recommendation model" actions={(
      <button type="button" className="btn btn--primary" onClick={retrain} disabled={busy}>
        {busy ? 'Retraining…' : '↻ Retrain now'}
      </button>
    )}>
      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && <LoadingSkeleton variant="cards" count={2} />}
      {data && (
        <>
          <ul className="stats stats--admin" aria-label="Model summary">
            <li className="stat"><span className="stat__value stat__value--small">{formatDateTime(data.fitted_at)}</span>
              <span className="stat__label">Last trained</span></li>
            <li className="stat"><span className="stat__value">{data.n_opportunities}</span>
              <span className="stat__label">Open opportunities in the model</span></li>
            <li className="stat"><span className="stat__value">{data.unit_idf.length} / {data.skill_idf.length}</span>
              <span className="stat__label">Units / skills learnt</span></li>
          </ul>

          <section className="panel">
            <h2 className="small-heading">Match weights (read-only)</h2>
            <ul className="weights">
              {Object.entries(data.match_weights).map(([k, v]) => (
                <li key={k}><span className="weights__value">{Math.round(v * 100)}%</span> {k}</li>
              ))}
            </ul>
            <p className="muted small">Match score = 60% grades (TF-IDF + cosine) + 25% skills (TF-IDF + cosine)
              + 15% interests. Set in backend/app/config.py (MATCH_WEIGHTS).</p>
          </section>

          <div className="two-col">
            <SortableIdf title="Unit IDF weights" rows={data.unit_idf} />
            <SortableIdf title="Skill IDF weights" rows={data.skill_idf} />
          </div>

          {ablation.length > 0 && (
            <section className="panel">
              <h2 className="small-heading">Evaluation: ablation study</h2>
              <p className="muted small">50 labelled synthetic students (backend/evaluation). Top-1 = the expected
                internship ranked first.</p>
              <table className="table compact-table">
                <thead><tr><th>Inputs used</th><th>Group</th><th>Students</th><th>Top-1</th><th>Top-3</th></tr></thead>
                <tbody>
                  {labelled.map((r) => (
                    <tr key={`${r.config}-${r.group}`} className={r.group === 'all_labelled' ? 'row--strong' : ''}>
                      <td data-label="Inputs used">{CONFIG_LABELS[r.config] ?? r.config}</td>
                      <td data-label="Group">{r.group.replace('_', ' ')}</td>
                      <td data-label="Students">{r.n}</td>
                      <td data-label="Top-1">{pct(r.top1)}</td>
                      <td data-label="Top-3">{pct(r.top3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {conflicting.length > 0 && (
                <>
                  <h3 className="small-heading">Conflicting students (grades vs interests)</h3>
                  <table className="table compact-table">
                    <thead><tr><th>Inputs used</th><th>Grade side wins</th><th>Interest side wins</th><th>Other</th></tr></thead>
                    <tbody>
                      {conflicting.map((r) => (
                        <tr key={r.config}>
                          <td data-label="Inputs used">{CONFIG_LABELS[r.config] ?? r.config}</td>
                          <td data-label="Grade side wins">{r.grade_side_wins}</td>
                          <td data-label="Interest side wins">{r.interest_side_wins}</td>
                          <td data-label="Other">{r.other_wins}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </section>
          )}
        </>
      )}
      <Toast message={toast} onDone={clearToast} />
    </AdminLayout>
  );
}
