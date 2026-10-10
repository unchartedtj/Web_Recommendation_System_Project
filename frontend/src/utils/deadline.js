/**
 * Deadline helpers for internship cards, e.g. "Closes in 5 days".
 * Dates come from the API as "YYYY-MM-DD" and are compared using the LOCAL date.
 */

/** Whole days from today until the date (0 = today, negative = already passed). */
export function daysUntil(isoDate, today = new Date()) {
  if (!isoDate) return null;
  const [y, m, d] = isoDate.split('-').map(Number);
  const target = new Date(y, m - 1, d);                       // local midnight
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((target - start) / 86_400_000);           // ms in a day
}

/** { label, urgent } for display. urgent = closes in under 7 days. */
export function closesIn(isoDate, today = new Date()) {
  const days = daysUntil(isoDate, today);
  if (days === null) return { label: 'No deadline', urgent: false };
  if (days < 0) return { label: 'Closed', urgent: false };
  if (days === 0) return { label: 'Closes today', urgent: true };
  if (days === 1) return { label: 'Closes tomorrow', urgent: true };
  return { label: `Closes in ${days} days`, urgent: days < 7 };
}

/** "12 Dec 2026" style date for display. */
export function formatDate(iso) {
  if (!iso) return '—';
  const date = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}
