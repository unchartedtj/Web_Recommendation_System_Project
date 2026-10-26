/**
 * The route guard: only admins reach /admin, and a user who must change their password is
 * sent to the Change password page whatever they try to open.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { TOKEN_KEY, USER_KEY } from '../api/client.js';
import ProtectedRoute from '../components/ProtectedRoute.jsx';
import { AuthProvider } from '../context/AuthContext.jsx';

// The AuthProvider refreshes the user on load; keep that request pending so it changes nothing.
vi.mock('../api/auth.js', () => ({ fetchMe: () => new Promise(() => {}), login: vi.fn() }));

function signIn(user) {
  localStorage.setItem(TOKEN_KEY, 'test-token');
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<p>Login page</p>} />
          <Route element={<ProtectedRoute allowedRoles={['system_admin']} />}>
            <Route path="/admin" element={<p>Admin overview</p>} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['student']} />}>
            <Route path="/student" element={<p>Student dashboard</p>} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="/account/password" element={<p>Change password page</p>} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

afterEach(() => localStorage.clear());

it('lets an admin open the admin dashboard', () => {
  signIn({ user_id: 1, role: 'system_admin', name: 'Admin', must_change_password: false });
  renderAt('/admin');
  expect(screen.getByText('Admin overview')).toBeInTheDocument();
});

it('sends a student who opens /admin back to their own dashboard', () => {
  signIn({ user_id: 2, role: 'student', name: 'Sam', must_change_password: false });
  renderAt('/admin');
  expect(screen.getByText('Student dashboard')).toBeInTheDocument();
  expect(screen.queryByText('Admin overview')).not.toBeInTheDocument();
});

it('sends a logged-out visitor to the login page', () => {
  renderAt('/admin');
  expect(screen.getByText('Login page')).toBeInTheDocument();
});

it('forces a password change before any other page', () => {
  signIn({ user_id: 1, role: 'system_admin', name: 'Admin', must_change_password: true });
  renderAt('/admin');
  expect(screen.getByText('Change password page')).toBeInTheDocument();
  expect(screen.queryByText('Admin overview')).not.toBeInTheDocument();
});
