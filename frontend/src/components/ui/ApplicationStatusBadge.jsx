/**
 * An application's status as a pill: icon + text (never colour alone).
 */
const LOOK = {
  pending: { icon: '⏳', label: 'Pending' },
  shortlisted: { icon: '★', label: 'Shortlisted' },
  accepted: { icon: '✓', label: 'Accepted' },
  rejected: { icon: '✗', label: 'Rejected' },
  withdrawn: { icon: '↩', label: 'Withdrawn' },
};

export default function ApplicationStatusBadge({ status }) {
  const look = LOOK[status] ?? { icon: '', label: status };
  return (
    <span className={`app-status app-status--${status}`}>
      <span aria-hidden="true">{look.icon}</span> {look.label}
    </span>
  );
}

export const STATUS_LABELS = Object.fromEntries(Object.entries(LOOK).map(([k, v]) => [k, v.label]));
