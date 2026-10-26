/**
 * The SUS questionnaire form: all 10 answers are required, and no score is ever shown.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SusForm from '../components/SusForm.jsx';

const questions = Array.from({ length: 10 }, (_, i) => `Statement number ${i + 1}`);
const scale = ['Strongly disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly agree'];

it('keeps Submit disabled until all 10 statements are answered', async () => {
  const onSubmit = vi.fn();
  render(<SusForm questions={questions} scale={scale} onSubmit={onSubmit} />);
  const submit = screen.getByRole('button', { name: 'Submit feedback' });
  expect(submit).toBeDisabled();
  expect(screen.getByText(/Still to answer: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10/)).toBeInTheDocument();

  const groups = screen.getAllByRole('group');
  for (const group of groups.slice(0, 9)) {
    await userEvent.click(group.querySelectorAll('input[type="radio"]')[2]);   // "Neutral"
  }
  expect(submit).toBeDisabled();
  expect(screen.getByText(/Still to answer: 10\./)).toBeInTheDocument();

  await userEvent.click(groups[9].querySelectorAll('input[type="radio"]')[4]);   // "Strongly agree"
  expect(submit).toBeEnabled();
  await userEvent.click(submit);
  expect(onSubmit).toHaveBeenCalledWith({
    q1: 3, q2: 3, q3: 3, q4: 3, q5: 3, q6: 3, q7: 3, q8: 3, q9: 3, q10: 5, comments: null,
  });
  expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
});

it('fills in previous answers', () => {
  const initial = Object.fromEntries(questions.map((_, i) => [`q${i + 1}`, 4]));
  render(<SusForm questions={questions} scale={scale} initial={{ ...initial, comments: 'Good' }} onSubmit={vi.fn()} />);
  expect(screen.getByRole('button', { name: 'Submit feedback' })).toBeEnabled();
  expect(screen.getByLabelText('Comments (optional)')).toHaveValue('Good');
});
