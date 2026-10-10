/**
 * Eligibility badge: "✓ Eligible" or "⚠ Below minimum".
 * Always icon + TEXT, never colour alone, so it's readable for colour-blind users.
 */
export default function StatusBadge({ eligible }) {
  return eligible ? (
    <span className="status status--ok">
      <span aria-hidden="true">✓</span> Eligible
    </span>
  ) : (
    <span className="status status--warn">
      <span aria-hidden="true">⚠</span> Below minimum
    </span>
  );
}
