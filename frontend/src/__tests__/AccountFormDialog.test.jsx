/**
 * The admin's Add student dialog sends the form to the API and shows field errors it returns.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AccountFormDialog from '../components/admin/AccountFormDialog.jsx';

it('sends the new student and shows the API field errors under each box', async () => {
  const onSave = vi.fn().mockRejectedValueOnce({
    message: 'Please fix the highlighted fields',
    fields: { email: 'Email is already registered' },
  });
  render(<AccountFormDialog kind="student" onSave={onSave} onCancel={() => {}} />);

  await userEvent.type(screen.getByLabelText('First name'), 'Achieng');
  await userEvent.type(screen.getByLabelText('Last name'), 'Otieno');
  await userEvent.type(screen.getByLabelText('Email'), 'achieng.otieno@strathmore.edu');
  await userEvent.type(screen.getByLabelText('Admission number'), '123456');
  await userEvent.type(screen.getByLabelText('Course'), 'BBIT');
  await userEvent.type(screen.getByLabelText('Password'), '12345678A');
  await userEvent.type(screen.getByLabelText('Confirm password'), '12345678A');
  await userEvent.click(screen.getByRole('button', { name: 'Create student' }));

  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
    first_name: 'Achieng', last_name: 'Otieno', email: 'achieng.otieno@strathmore.edu',
    admission_no: '123456', course: 'BBIT', year_of_study: 3, password: '12345678A',
  }));
  expect(await screen.findByText('Email is already registered')).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('Please fix the highlighted fields');
});

it('has no password boxes when editing', () => {
  render(<AccountFormDialog kind="partner" onSave={vi.fn()} onCancel={() => {}}
    initial={{ organization_name: 'Safaricom PLC', contact_person: 'Jane', email: 'hr@safaricom.co.ke', phone: '0712345678' }} />);
  expect(screen.getByLabelText('Organisation')).toHaveValue('Safaricom PLC');
  expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Save changes' })).toBeInTheDocument();
});
