/**
 * The "Transcript verification" section on My Profile shows the right status and uploads a PDF.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { uploadTranscript } from '../api/student.js';
import TranscriptSection from '../components/student/TranscriptSection.jsx';

vi.mock('../api/student.js', () => ({ uploadTranscript: vi.fn(), openMyTranscript: vi.fn() }));

it('shows "Not uploaded" and uploads a chosen PDF', async () => {
  const onUploaded = vi.fn();
  uploadTranscript.mockResolvedValue({ status: 'pending', original_name: 't.pdf', uploaded_at: '2026-11-02T10:00:00Z' });
  render(<TranscriptSection transcript={null} onUploaded={onUploaded} />);
  expect(screen.getByText('Not uploaded')).toBeInTheDocument();

  const upload = screen.getByRole('button', { name: 'Upload' });
  expect(upload).toBeDisabled();
  const file = new File(['%PDF-1.4'], 't.pdf', { type: 'application/pdf' });
  await userEvent.upload(screen.getByLabelText(/Transcript \(PDF/), file);
  await userEvent.click(upload);
  expect(uploadTranscript).toHaveBeenCalledWith(file);
  expect(onUploaded).toHaveBeenCalledWith(expect.objectContaining({ status: 'pending' }));
});

it('shows the rejection reason', () => {
  render(<TranscriptSection onUploaded={() => {}} transcript={{
    status: 'rejected', review_reason: 'OOP mark does not match', original_name: 't.pdf',
    uploaded_at: '2026-11-02T10:00:00Z' }} />);
  expect(screen.getByText('Marks rejected')).toBeInTheDocument();
  expect(screen.getByText('OOP mark does not match')).toBeInTheDocument();
});
