/**
 * How an internship's pay is shown: "Unpaid", "Paid · KSh 25,000/month" or
 * "Stipend · KSh 10,000/month".
 */
export const PAY_TYPES = [
  { value: 'unpaid', label: 'Unpaid' },
  { value: 'paid', label: 'Paid' },
  { value: 'stipend', label: 'Stipend' },
];

export function formatPay(opp) {
  const type = opp?.compensation_type ?? 'unpaid';
  if (type === 'unpaid') return 'Unpaid';
  const label = type === 'paid' ? 'Paid' : 'Stipend';
  const amount = opp?.compensation_amount;
  return amount ? `${label} · KSh ${Number(amount).toLocaleString('en-KE')}/month` : label;
}
