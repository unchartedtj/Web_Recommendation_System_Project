/**
 * The streamlined admin menu: 5 sections in the sidebar, and tabs inside a grouped section.
 */
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminLayout from '../components/admin/AdminLayout.jsx';
import { AuthProvider } from '../context/AuthContext.jsx';

vi.mock('../api/auth.js', () => ({ fetchMe: () => new Promise(() => {}), login: vi.fn() }));

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><AdminLayout title="Partners"><p>page</p></AdminLayout></AuthProvider>
    </MemoryRouter>,
  );
}

it('shows 5 sections in the sidebar', () => {
  renderAt('/admin');
  const sidebar = screen.getByRole('navigation', { name: 'Admin sections' });
  const labels = within(sidebar).getAllByRole('link').map((a) => a.textContent.trim());
  expect(labels).toHaveLength(5);
  expect(labels.join(' | ')).toMatch(/Dashboard.*Placements.*People.*Internships.*Reports & settings/);
});

it('shows the People tabs and highlights the section on a People page', () => {
  renderAt('/admin/people/partners');
  const tabs = screen.getByRole('navigation', { name: 'People pages' });
  expect(within(tabs).getAllByRole('link').map((a) => a.textContent)).toEqual(['Students', 'Partners', 'All accounts']);
  expect(within(tabs).getByRole('link', { name: 'Partners' })).toHaveClass('active');
  const sidebar = screen.getByRole('navigation', { name: 'Admin sections' });
  expect(within(sidebar).getByRole('link', { name: /People/ })).toHaveClass('active');
});

it('shows no tabs on an ungrouped page', () => {
  renderAt('/admin/placements');
  expect(screen.queryByRole('navigation', { name: /pages$/ })).not.toBeInTheDocument();
});
