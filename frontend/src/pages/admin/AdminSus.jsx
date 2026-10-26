/**
 * SUS Results (/admin/sus), test case TC10: the mean System Usability Scale score with a
 * pass/fail against the target of 68, response count, per-role means, a distribution chart,
 * the average answer for each of the 10 statements, and Export CSV.
 */
import { useCallback, useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { downloadCsv, fetchSusResults } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';

const ROLE_LABELS = { student: 'Students', industry_partner: 'Industry partners' };

export default function AdminSus() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    fetchSusResults().then(setData).catch((err) => setError(parseApiError(err).message));
  }, []);
  useEffect(load, [load]);

  const exportCsv = () => downloadCsv('/admin/sus/export.csv', 'sus_responses.csv')
    .catch((err) => setError(parseApiError(err).message));

  return (
    <AdminLayout title="SUS results" actions={(
      <button type="button" className="btn btn--secondary" onClick={exportCsv} disabled={!data?.count}>
        ⬇ Export CSV
      </button>
    )}>
      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && <LoadingSkeleton variant="cards" count={2} />}
      {data?.count === 0 && (
        <EmptyState icon="📝" title="No responses yet">
          Students and partners answer from the account menu: Give feedback.
        </EmptyState>
      )}
      {data?.count > 0 && (
        <>
          <section className={`panel sus-score ${data.meets_target ? 'sus-score--pass' : 'sus-score--fail'}`}>
            <div>
              <p className="sus-score__value">{data.mean}</p>
              <p className="muted">Mean SUS score (0–100) from {data.count} {data.count === 1 ? 'response' : 'responses'}</p>
            </div>
            <p className="sus-score__verdict">
              {data.meets_target
                ? <><span aria-hidden="true">✓ </span>Meets the target of {data.target}</>
                : <><span aria-hidden="true">✗ </span>Below the target of {data.target}</>}
            </p>
          </section>

          <ul className="stats stats--admin" aria-label="SUS summary">
            <li className="stat"><span className="stat__value">{data.min}</span><span className="stat__label">Lowest score</span></li>
            <li className="stat"><span className="stat__value">{data.max}</span><span className="stat__label">Highest score</span></li>
            {Object.entries(data.by_role).map(([role, r]) => (
              <li key={role} className="stat"><span className="stat__value">{r.mean}</span>
                <span className="stat__label">{ROLE_LABELS[role] ?? role} ({r.count})</span></li>
            ))}
          </ul>

          <section className="panel chart-panel" aria-label="Score distribution">
            <h2 className="chart-panel__title">Score distribution</h2>
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.distribution} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="range" tick={{ fontSize: 11 }} interval={0} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0b3d91" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="panel">
            <h2 className="small-heading">Average answer per statement (1 = strongly disagree, 5 = strongly agree)</h2>
            <p className="muted small">Odd statements are positive (higher is better); even statements are
              negative (lower is better).</p>
            <table className="table compact-table">
              <thead><tr><th>#</th><th>Statement</th><th>Average</th></tr></thead>
              <tbody>
                {data.items.map((i) => (
                  <tr key={i.number}>
                    <td data-label="#">{i.number}</td>
                    <td data-label="Statement">{i.statement}</td>
                    <td data-label="Average">{i.average}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </AdminLayout>
  );
}
