/**
 * The partner's Candidates page lists applicants sorted by match % (best first).
 * The API module is mocked, so no backend is needed.
 */
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { fetchCandidates } from '../api/opportunities.js';
import { AuthProvider } from '../context/AuthContext.jsx';
import Candidates from '../pages/partner/Candidates.jsx';

vi.mock('../api/opportunities.js', () => ({ fetchCandidates: vi.fn(), decideApplication: vi.fn() }));

function candidate(id, name, score, status = 'pending') {
  return {
    application_id: id, status, status_reason: null, application_date: '2026-10-01T09:00:00Z',
    match_score: score, match_percent: score * 100, meets_requirements: true,
    breakdown: { grade_score: score, skill_score: score, interest_score: 1 },
    units: [], skills: [], interests: [], interest_match: true, motivation_note: null, placement: null,
    student: { student_id: id, name, admission_no: `9000${id}`, course: 'BBIT', year_of_study: 3, email: null },
  };
}

it('renders candidates sorted by match % with counts', async () => {
  fetchCandidates.mockResolvedValue({
    opportunity: { opportunity_id: 1, title: 'Software Development Intern', status: 'open',
      slots: 3, slots_filled: 0, application_deadline: '2099-01-01' },
    counts: { all: 3, pending: 2, shortlisted: 1, accepted: 0, rejected: 0, withdrawn: 0 },
    // Deliberately out of order: the page must show them best match first.
    candidates: [candidate(1, 'Low Match', 0.4), candidate(2, 'Top Match', 0.9, 'shortlisted'),
      candidate(3, 'Mid Match', 0.6)],
  });
  render(
    <MemoryRouter initialEntries={['/partner/opportunities/1/candidates']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes><Route path="/partner/opportunities/:id/candidates" element={<Candidates />} /></Routes>
      </AuthProvider>
    </MemoryRouter>,
  );

  const cards = await screen.findAllByTestId('candidate');
  const names = cards.map((c) => within(c).getByRole('heading', { level: 3 }).textContent);
  expect(names).toEqual(['Top Match', 'Mid Match', 'Low Match']);
  expect(screen.getByRole('heading', { level: 1, name: 'Software Development Intern' })).toBeInTheDocument();
  expect(screen.getByText('0/3')).toBeInTheDocument();
  // The shortlisted candidate can't be shortlisted again; pending ones can.
  expect(within(cards[0]).queryByRole('button', { name: 'Shortlist' })).not.toBeInTheDocument();
  expect(within(cards[1]).getByRole('button', { name: 'Shortlist' })).toBeInTheDocument();
});
