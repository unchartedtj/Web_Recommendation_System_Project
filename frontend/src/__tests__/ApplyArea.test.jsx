/**
 * The Apply area on the internship details page shows the right state for each case.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ApplyArea from '../components/student/ApplyArea.jsx';
import { applyState } from '../utils/applyState.js';

vi.mock('../api/applications.js', () => ({ applyToOpportunity: vi.fn() }));

const TODAY = new Date(2026, 9, 20);   // 20 Oct 2026

function data(overrides = {}) {
  return {
    opportunity: { opportunity_id: 1, title: 'Software Development Intern', status: 'open',
      application_deadline: '2099-01-01' },
    profile_complete: true,
    my_application: null,
    has_placement: false,
    my_match: { match_percent: 80, meets_requirements: true, unmet_requirements: [] },
    ...overrides,
  };
}

function renderArea(d) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ApplyArea data={d} onApplied={() => {}} />
    </MemoryRouter>,
  );
}

describe('applyState', () => {
  it('returns each of the five states', () => {
    expect(applyState(data(), TODAY)).toBe('can_apply');
    expect(applyState(data({ profile_complete: false }), TODAY)).toBe('incomplete');
    expect(applyState(data({ my_application: { application_id: 3, status: 'pending' } }), TODAY)).toBe('applied');
    expect(applyState(data({ has_placement: true }), TODAY)).toBe('placed');
    const expired = data({ opportunity: { ...data().opportunity, application_deadline: '2026-10-19' } });
    expect(applyState(expired, TODAY)).toBe('closed');
  });

  it('shows "applied" (not "placed") for the student\'s own accepted application', () => {
    const d = data({ has_placement: true, my_application: { application_id: 3, status: 'accepted' } });
    expect(applyState(d, TODAY)).toBe('applied');
  });
});

describe('ApplyArea', () => {
  it('shows the Apply button when the student can apply', () => {
    renderArea(data());
    expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument();
  });

  it('asks for a complete profile first', () => {
    renderArea(data({ profile_complete: false }));
    expect(screen.getByRole('link', { name: 'Complete your profile to apply' }))
      .toHaveAttribute('href', '/student/profile');
    expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument();
  });

  it('shows the application status once applied', () => {
    renderArea(data({ my_application: { application_id: 3, status: 'shortlisted' } }));
    expect(screen.getByText(/Applied:/)).toBeInTheDocument();
    expect(screen.getByText('Shortlisted')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View my applications' }))
      .toHaveAttribute('href', '/student/applications');
  });

  it('says applications are closed after the deadline', () => {
    renderArea(data({ opportunity: { ...data().opportunity, application_deadline: '2000-01-01' } }));
    expect(screen.getByText('Applications closed')).toBeInTheDocument();
  });

  it('blocks a student who already has a placement', () => {
    renderArea(data({ has_placement: true }));
    expect(screen.getByText('You already have a confirmed placement.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument();
  });
});
