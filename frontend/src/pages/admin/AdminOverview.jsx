/**
 * Admin Overview (/admin): headline numbers, three bar charts and the latest activity.
 */
import { useCallback, useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fetchOverview } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import ActivityList from '../../components/admin/ActivityList.jsx';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function Chart({ title, data, xKey = 'name', color = '#0b3d91' }) {
  const empty = data.every((d) => !d.count);
  return (
    <section className="panel chart-panel" aria-label={title}>
      <h2 className="chart-panel__title">{title}</h2>
      {empty ? <p className="muted">No data yet.</p> : (
        <div className="chart-box">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey={xKey} tick={{ fontSize: 11 }} interval={0} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill={color} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {/* The same numbers as text, for screen readers and printing. */}
      <ul className="visually-hidden">
        {data.map((d) => <li key={d[xKey]}>{d[xKey]}: {d.count}</li>)}
      </ul>
    </section>
  );
}

export default function AdminOverview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    fetchOverview().then(setData).catch((err) => setError(parseApiError(err).message));
  }, []);
  useEffect(load, [load]);

  const toChart = (obj) => Object.entries(obj).map(([name, count]) => ({ name: cap(name), count }));
  const placementsTotal = data ? Object.values(data.placements).reduce((a, b) => a + b, 0) : 0;
  const applicationsTotal = data ? Object.values(data.applications).reduce((a, b) => a + b, 0) : 0;

  return (
    <AdminLayout title="Overview">
      <ErrorBanner message={error} onRetry={load} />
      {!data && !error && <LoadingSkeleton variant="cards" count={3} />}
      {data && (
        <>
          <ul className="stats stats--admin" aria-label="Key numbers">
            <li className="stat"><span className="stat__value">{data.students.total}</span>
              <span className="stat__label">Students ({data.students.complete_profiles} with complete profiles)</span></li>
            <li className="stat"><span className="stat__value">{data.partners}</span>
              <span className="stat__label">Industry partners</span></li>
            <li className="stat"><span className="stat__value">{data.open_opportunities}</span>
              <span className="stat__label">Open opportunities</span></li>
            <li className="stat"><span className="stat__value">{applicationsTotal}</span>
              <span className="stat__label">Applications</span></li>
            <li className="stat"><span className="stat__value">{placementsTotal}</span>
              <span className="stat__label">Placements</span></li>
            <li className="stat">
              <span className="stat__value">
                {data.match.accepted_avg_percent != null ? `${Math.round(data.match.accepted_avg_percent)}%` : '—'}
              </span>
              <span className="stat__label">
                Avg match of accepted applications
                {data.match.all_avg_percent != null && ` (all: ${Math.round(data.match.all_avg_percent)}%)`}
              </span>
            </li>
          </ul>

          <div className="chart-grid">
            <Chart title="Placements by status" data={toChart(data.placements)} color="#1b5e20" />
            <Chart title="Applications by status" data={toChart(data.applications)} />
            <Chart title="Opportunities by sector" xKey="sector" data={data.opportunities_per_sector}
              color="#6a1b9a" />
          </div>

          <section className="panel">
            <h2 className="section-title">Recent activity</h2>
            <ActivityList items={data.recent_activity} />
          </section>
        </>
      )}
    </AdminLayout>
  );
}
