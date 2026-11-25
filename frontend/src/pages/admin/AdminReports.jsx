/**
 * Admin Reports (/admin/reports/summary):
 *   1. Placement rate by course
 *   2. Match % vs application outcome (does a higher match lead to acceptance?)
 *   3. Pay: unpaid, paid and stipend internships with KSh amounts
 * Each report has an Export CSV button.
 */
import { useCallback, useEffect, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { downloadCsv, fetchReports } from '../../api/admin.js';
import { parseApiError } from '../../api/client.js';
import AdminLayout from '../../components/admin/AdminLayout.jsx';
import ErrorBanner from '../../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../../components/ui/LoadingSkeleton.jsx';

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const pct = (v) => (v == null ? '—' : `${v}%`);
// Pie colours: unpaid grey, paid green, stipend blue.
const PAY_COLORS = { unpaid: '#9aa5b1', paid: '#1b5e20', stipend: '#0b3d91' };

function PayPie({ rows }) {
  const data = rows.filter((r) => r.internships).map((r) => ({ name: cap(r.type), type: r.type, value: r.internships }));
  const total = data.reduce((sum, d) => sum + d.value, 0);
  if (!total) return <p className="muted">No internships yet.</p>;
  return (
    <div className="chart-box chart-box--pie">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius="75%"
            label={({ name, value }) => `${name}: ${Math.round((value * 100) / total)}%`}>
            {data.map((d) => <Cell key={d.type} fill={PAY_COLORS[d.type]} />)}
          </Pie>
          <Tooltip formatter={(v) => `${v} internship${v === 1 ? '' : 's'}`} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

const ksh = (v) => (v == null ? '—' : `KSh ${Number(v).toLocaleString('en-KE')}`);

function BarPanel({ data, dataKey, xKey, color, unit = '', max }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} interval={0} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} domain={[0, max ?? 'auto']} unit={unit} />
          <Tooltip formatter={(v) => `${v}${unit}`} />
          <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** The section heading with an "Export CSV" button on the right. */
function ReportHeading({ id, title, csv, onExport }) {
  return (
    <div className="report__head">
      <h2 id={id} className="section-title">{title}</h2>
      <button type="button" className="btn btn--secondary btn--sm" onClick={() => onExport(csv)}>
        ⬇ Export CSV
      </button>
    </div>
  );
}

const CSV = {
  placement: ['/admin/reports/placement-rate.csv', 'placement_rate_by_course.csv'],
  match: ['/admin/reports/match-outcomes.csv', 'match_vs_outcome.csv'],
  pay: ['/admin/reports/pay.csv', 'internship_pay.csv'],
};

export default function AdminReports() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    fetchReports().then(setData).catch((err) => setError(parseApiError(err).message));
  }, []);
  useEffect(load, [load]);
  const [exportError, setExportError] = useState('');
  const exportCsv = ([url, filename]) => {
    setExportError('');
    downloadCsv(url, filename).catch((err) => setExportError(parseApiError(err).message));
  };

  const rate = data?.placement_rate;
  const rateChart = rate?.rows.map((r) => ({ course: r.course, rate: r.rate_percent ?? 0 }));
  const matchChart = data?.match_outcomes.filter((r) => r.applications)
    .map((r) => ({ status: cap(r.status), match: r.avg_match_percent }));

  return (
    <AdminLayout title="Reports">
      <ErrorBanner message={error} onRetry={load} />
      <ErrorBanner message={exportError} />
      {!data && !error && <LoadingSkeleton variant="cards" count={3} />}
      {data && (
        <>
          {/* ---------- 1. Placement rate ---------- */}
          <section className="panel report" aria-labelledby="report-placement">
            <ReportHeading id="report-placement" title="Placement rate by course" csv={CSV.placement} onExport={exportCsv} />
            <p className="muted small">
              Placed = a confirmed, ongoing or completed placement. Overall: <strong>{rate.total.placed}</strong> of{' '}
              <strong>{rate.total.students}</strong> students placed ({pct(rate.total.rate_percent)}).
            </p>
            <BarPanel data={rateChart} dataKey="rate" xKey="course" color="#1b5e20" unit="%" max={100} />
            <div className="table-wrap">
              <table className="table admin-table report__table">
                <caption className="visually-hidden">Placement rate by course</caption>
                <thead><tr><th>Course</th><th>Students</th><th>Complete profiles</th><th>Placed</th><th>Placement rate</th></tr></thead>
                <tbody>
                  {rate.rows.map((r) => (
                    <tr key={r.course}>
                      <td>{r.course}</td><td>{r.students}</td>
                      <td>{r.complete_profiles}</td><td>{r.placed}</td><td>{pct(r.rate_percent)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr><th>All students</th><th>{rate.total.students}</th><th>{rate.total.complete_profiles}</th>
                    <th>{rate.total.placed}</th><th>{pct(rate.total.rate_percent)}</th></tr>
                </tfoot>
              </table>
            </div>
          </section>

          {/* ---------- 2. Match % vs outcome ---------- */}
          <section className="panel report" aria-labelledby="report-match">
            <ReportHeading id="report-match" title="Match % vs application outcome" csv={CSV.match} onExport={exportCsv} />
            <p className="muted small">
              The average match students had when they applied, for each outcome. If accepted applications
              have higher matches, the recommendations are pointing students to suitable internships.
            </p>
            {matchChart.length > 0 && <BarPanel data={matchChart} dataKey="match" xKey="status" unit="%" max={100} color="#0b3d91" />}
            <div className="table-wrap">
              <table className="table admin-table report__table">
                <caption className="visually-hidden">Match percentage by application outcome</caption>
                <thead><tr><th>Outcome</th><th>Applications</th><th>Average match</th><th>Lowest</th><th>Highest</th></tr></thead>
                <tbody>
                  {data.match_outcomes.map((r) => (
                    <tr key={r.status}>
                      <td>{cap(r.status)}</td><td>{r.applications}</td><td>{pct(r.avg_match_percent)}</td>
                      <td>{pct(r.min_match_percent)}</td><td>{pct(r.max_match_percent)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ---------- 3. Pay ---------- */}
          <section className="panel report" aria-labelledby="report-pay">
            <ReportHeading id="report-pay" title="Internship pay" csv={CSV.pay} onExport={exportCsv} />
            <p className="muted small">Amounts are in KSh per month.</p>
            <PayPie rows={data.pay} />
            <ul className="stats stats--admin" aria-label="Internships by pay type">
              {data.pay.map((r) => (
                <li className="stat" key={r.type}>
                  <span className="stat__value">{r.internships}</span>
                  <span className="stat__label">{cap(r.type)} ({r.open} open)</span>
                </li>
              ))}
            </ul>
            <div className="table-wrap">
              <table className="table admin-table report__table">
                <caption className="visually-hidden">Internship pay summary</caption>
                <thead><tr><th>Pay</th><th>Internships</th><th>Open</th><th>Average</th><th>Lowest</th><th>Highest</th></tr></thead>
                <tbody>
                  {data.pay.map((r) => (
                    <tr key={r.type}>
                      <td>{cap(r.type)}</td><td>{r.internships}</td><td>{r.open}</td>
                      <td>{r.type === 'unpaid' ? '—' : ksh(r.avg_amount)}</td>
                      <td>{r.type === 'unpaid' ? '—' : ksh(r.min_amount)}</td>
                      <td>{r.type === 'unpaid' ? '—' : ksh(r.max_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </AdminLayout>
  );
}
