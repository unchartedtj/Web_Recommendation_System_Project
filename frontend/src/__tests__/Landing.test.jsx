/**
 * The public landing page shows its heading and the two main buttons.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext.jsx';
import Landing from '../pages/Landing.jsx';

it('renders the heading and the Log in / Create an account buttons', () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><Landing /></AuthProvider>
    </MemoryRouter>,
  );
  expect(screen.getByRole('heading', { level: 1, name: 'Welcome to the WBL Placement Portal' }))
    .toBeInTheDocument();
  expect(screen.getByRole('img', { name: 'Strathmore University logo' })).toBeInTheDocument();
  const hero = screen.getByRole('region', { name: 'Welcome to the WBL Placement Portal' });
  expect(hero.querySelector('a[href="/login"]')).toHaveTextContent('Log in');
  expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute('href', '/register');
});
