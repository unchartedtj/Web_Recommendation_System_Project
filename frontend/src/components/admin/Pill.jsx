/**
 * Small status pills for admin tables: placement status, account status, open/closed.
 * Always icon + text, never colour alone.
 */
const PLACEMENT = {
  confirmed: { icon: '✓', label: 'Confirmed' },
  ongoing: { icon: '▶', label: 'Ongoing' },
  completed: { icon: '★', label: 'Completed' },
  terminated: { icon: '✗', label: 'Terminated' },
};

export function PlacementStatusPill({ status }) {
  const look = PLACEMENT[status] ?? { icon: '', label: status };
  return (
    <span className={`pill pill--${status}`}>
      <span aria-hidden="true">{look.icon}</span> {look.label}
    </span>
  );
}

export function ActivePill({ active }) {
  return active
    ? <span className="pill pill--active"><span aria-hidden="true">●</span> Active</span>
    : <span className="pill pill--inactive"><span aria-hidden="true">○</span> Deactivated</span>;
}

export const PLACEMENT_LABELS = Object.fromEntries(Object.entries(PLACEMENT).map(([k, v]) => [k, v.label]));
