/**
 * How an internship's pay is shown to students.
 */
import { formatPay } from '../utils/pay.js';

it('shows unpaid internships as Unpaid', () => {
  expect(formatPay({ compensation_type: 'unpaid', compensation_amount: null })).toBe('Unpaid');
  expect(formatPay({})).toBe('Unpaid');
});

it('shows the amount in KSh per month for paid and stipend internships', () => {
  expect(formatPay({ compensation_type: 'paid', compensation_amount: 25000 }))
    .toBe('Paid · KSh 25,000/month');
  expect(formatPay({ compensation_type: 'stipend', compensation_amount: 8000 }))
    .toBe('Stipend · KSh 8,000/month');
});
