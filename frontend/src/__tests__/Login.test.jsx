/**
 * The login page shows the Strathmore logo, the welcome heading and the login form.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext.jsx';
import Login from '../pages/Login.jsx';

it('renders the logo, the welcome heading and the form', () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><Login /></AuthProvider>
    </MemoryRouter>,
  );
  expect(screen.getByRole('img', { name: 'Strathmore University logo' })).toBeInTheDocument();
  expect(screen.getByRole('heading', { level: 1, name: 'Welcome to the WBL Placement Portal' }))
    .toBeInTheDocument();
  expect(screen.getByLabelText('Username')).toBeInTheDocument();
  expect(screen.getByLabelText('Password')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute('href', '/register');
});
