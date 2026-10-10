import { render, screen } from '@testing-library/react';
import MatchBar from '../components/ui/MatchBar.jsx';

describe('MatchBar', () => {
  it('shows the rounded percentage and exposes it to screen readers', () => {
    render(<MatchBar percent={71.6} />);
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '72');
  });

  it('keeps the value within 0 to 100', () => {
    render(<MatchBar percent={140} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });
});
