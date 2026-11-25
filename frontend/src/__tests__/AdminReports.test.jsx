/**
 * The admin Reports page shows the three reports: placement rate, match vs outcome, pay.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext.jsx';
import AdminReports from '../pages/admin/AdminReports.jsx';

vi.mock('../api/auth.js', () => ({ fetchMe: () => new Promise(() => {}), login: vi.fn() }));
const downloadCsv = vi.fn(() => Promise.resolve());
vi.mock('../api/admin.js', () => ({
  downloadCsv: (...args) => downloadCsv(...args),
  fetchReports: () => Promise.resolve({
    placement_rate: {
      rows: [{ course: 'BBIT', students: 4, complete_profiles: 4, placed: 3, rate_percent: 75 }],
      total: { students: 4, complete_profiles: 4, placed: 3, rate_percent: 75 },
    },
    match_outcomes: [
      { status: 'accepted', applications: 2, avg_match_percent: 72.5, min_match_percent: 70, max_match_percent: 75 },
      { status: 'rejected', applications: 1, avg_match_percent: 55, min_match_percent: 55, max_match_percent: 55 },
    ],
    pay: [
      { type: 'unpaid', internships: 3, open: 3, avg_amount: null, min_amount: null, max_amount: null },
      { type: 'paid', internships: 1, open: 1, avg_amount: 30000, min_amount: 30000, max_amount: 30000 },
      { type: 'stipend', internships: 0, open: 0, avg_amount: null, min_amount: null, max_amount: null },
    ],
  }),
}));
// Charts need real browser sizes; the tables carry the same numbers.
vi.mock('recharts', async () => {
  const Stub = ({ children }) => <div>{children}</div>;
  return {
    Bar: Stub, BarChart: Stub, CartesianGrid: Stub, Cell: Stub, Legend: Stub, Pie: Stub, PieChart: Stub,
    ResponsiveContainer: Stub, Tooltip: Stub, XAxis: Stub, YAxis: Stub,
  };
});

it('shows placement rate, match vs outcome and pay', async () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><AdminReports /></AuthProvider>
    </MemoryRouter>,
  );
  const placement = await screen.findByRole('table', { name: 'Placement rate by course' });
  expect(within(placement).getAllByText('75%').length).toBeGreaterThan(0);

  const match = screen.getByRole('table', { name: 'Match percentage by application outcome' });
  expect(within(match).getByText('72.5%')).toBeInTheDocument();
  expect(within(match).getByText('Rejected')).toBeInTheDocument();

  const pay = screen.getByRole('table', { name: 'Internship pay summary' });
  expect(within(pay).getAllByText('KSh 30,000').length).toBe(3);
});

it('each report has an Export CSV button that downloads its own file', async () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><AdminReports /></AuthProvider>
    </MemoryRouter>,
  );
  const buttons = await screen.findAllByRole('button', { name: /Export CSV/ });
  expect(buttons).toHaveLength(3);
  for (const b of buttons) await userEvent.click(b);
  expect(downloadCsv.mock.calls.map((c) => c[1])).toEqual(
    ['placement_rate_by_course.csv', 'match_vs_outcome.csv', 'internship_pay.csv']);
});
