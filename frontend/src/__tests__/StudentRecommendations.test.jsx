/**
 * Tests for the Recommendations page. The API module is replaced by a mock (vi.mock),
 * so no backend is needed.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { fetchRecommendations } from '../api/student.js';
import { AuthProvider } from '../context/AuthContext.jsx';
import StudentRecommendations from '../pages/student/StudentRecommendations.jsx';

vi.mock('../api/student.js', () => ({ fetchRecommendations: vi.fn() }));

function rec(id, title, score, eligible, sectorId = 1, sector = 'Software Development') {
  return {
    opportunity_id: id, title, organization: 'Demo Co', sector_id: sectorId, sector,
    location: 'Nairobi', application_deadline: '2099-01-01', duration_months: 3, slots: 2,
    match_score: score, match_percent: score * 100, rank: 0, meets_requirements: eligible,
    interest_match: false, unmet_requirements: [], missing_essential_skills: [],
    missing_desirable_skills: [], breakdown: { grade_score: score, skill_score: 0, interest_score: 0 },
    units: [], skills: [],
  };
}

function renderPage(data, url = '/student/recommendations') {
  fetchRecommendations.mockResolvedValue(data);
  return render(
    <MemoryRouter initialEntries={[url]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><StudentRecommendations /></AuthProvider>
    </MemoryRouter>,
  );
}

const DATA = {
  profile_complete: true,
  profile_updated_at: '2026-10-10T09:00:00Z',
  generated_at: '2026-10-10T09:00:00Z',
  // Deliberately out of order: the page must still show best match first.
  eligible: [rec(1, 'Alpha Intern', 0.41, true), rec(2, 'Bravo Intern', 0.77, true, 2, 'Data Analytics & AI'),
    rec(3, 'Charlie Intern', 0.58, true)],
  not_eligible: [rec(4, 'Delta Intern', 0.33, false), rec(5, 'Echo Intern', 0.52, false)],
};

const cardTitles = (container) =>
  within(container).getAllByRole('heading', { level: 3 }).map((h) => h.textContent);

describe('Recommendations page', () => {
  it('renders cards in descending match order within each section', async () => {
    renderPage(DATA);
    const eligible = await screen.findByTestId('eligible-list');
    expect(cardTitles(eligible)).toEqual(['Bravo Intern', 'Charlie Intern', 'Alpha Intern']);
    expect(screen.getByText('★ Top match')).toBeInTheDocument();

    // "Below minimum" is collapsed by default, with a count.
    expect(screen.queryByTestId('below-list')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /show 2 more internships/i }));
    expect(cardTitles(screen.getByTestId('below-list'))).toEqual(['Echo Intern', 'Delta Intern']);
  });

  it('shows the empty state when the profile is incomplete', async () => {
    renderPage({ profile_complete: false, profile_updated_at: null, generated_at: null,
      eligible: [], not_eligible: [] });
    expect(await screen.findByText(/complete your profile to see recommendations/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /complete your profile/i })).toHaveAttribute('href', '/student/profile');
  });

  it('filtering by sector hides cards without changing the order', async () => {
    renderPage(DATA, '/student/recommendations?sector=1');
    const eligible = await screen.findByTestId('eligible-list');
    // Bravo (sector 2) is hidden; the others keep their order and rank numbers.
    expect(cardTitles(eligible)).toEqual(['Charlie Intern', 'Alpha Intern']);
    expect(within(eligible).getByLabelText('Rank 2')).toBeInTheDocument();
  });

  it('"Eligible only" hides the below-minimum section', async () => {
    renderPage(DATA, '/student/recommendations?eligible=1');
    await screen.findByTestId('eligible-list');
    expect(screen.queryByText('Below minimum requirements')).not.toBeInTheDocument();
  });
});
