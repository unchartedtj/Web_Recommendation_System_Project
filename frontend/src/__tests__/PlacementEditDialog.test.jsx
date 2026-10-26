/**
 * The admin's placement edit dialog checks the rules BEFORE calling the API.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PlacementEditDialog, { validatePlacementEdit } from '../components/admin/PlacementEditDialog.jsx';

const placement = {
  placement_id: 7, status: 'confirmed', allowed_next: ['ongoing', 'terminated'],
  start_date: null, end_date: null,
  student: { name: 'Samuel Kamau' }, company: { name: 'TechCorp Kenya' },
  opportunity: { title: 'Software Development Intern' },
};

it('requires a reason to terminate, and does not call the API without one', async () => {
  const onSave = vi.fn();
  render(<PlacementEditDialog placement={placement} onSave={onSave} onCancel={() => {}} />);
  await userEvent.selectOptions(screen.getByLabelText('Status'), 'terminated');
  await userEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(screen.getByText('A reason is required to terminate a placement')).toBeInTheDocument();
  expect(onSave).not.toHaveBeenCalled();

  await userEvent.type(screen.getByLabelText(/Reason/), 'Student left the company');
  await userEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
    status: 'terminated', reason: 'Student left the company' }));
});

it('blocks an end date before the start date, and ongoing without a start date', async () => {
  const onSave = vi.fn();
  render(<PlacementEditDialog placement={placement} onSave={onSave} onCancel={() => {}} />);
  await userEvent.selectOptions(screen.getByLabelText('Status'), 'ongoing');
  await userEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(screen.getByText('A start date is required once the placement is ongoing')).toBeInTheDocument();

  await userEvent.type(screen.getByLabelText('Start date'), '2027-02-01');
  await userEvent.type(screen.getByLabelText('End date'), '2027-01-01');
  await userEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(screen.getByText('The end date must be after the start date')).toBeInTheDocument();
  expect(onSave).not.toHaveBeenCalled();
});

it('only offers the allowed next statuses', () => {
  render(<PlacementEditDialog placement={placement} onSave={vi.fn()} onCancel={() => {}} />);
  const options = [...screen.getByLabelText('Status').options].map((o) => o.value);
  expect(options).toEqual(['confirmed', 'ongoing', 'terminated']);
});

it('validatePlacementEdit accepts a valid change', () => {
  expect(validatePlacementEdit({ status: 'ongoing', start_date: '2027-01-01', end_date: '2027-04-01', reason: '' }))
    .toEqual({});
});
