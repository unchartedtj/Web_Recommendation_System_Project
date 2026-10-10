/**
 * A horizontal percentage bar with the number next to it, e.g. [██████░░░░] 63%.
 * role="progressbar" + aria-valuenow lets screen readers announce the value.
 */
export default function MatchBar({ percent, label = 'Match', size = 'md' }) {
  const value = Math.max(0, Math.min(100, Number(percent) || 0));
  const rounded = Math.round(value);
  return (
    <div className={`match-bar match-bar--${size}`}>
      <div
        className="match-bar__track"
        role="progressbar"
        aria-label={label}
        aria-valuenow={rounded}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="match-bar__fill" style={{ width: `${value}%` }} />
      </div>
      <span className="match-bar__value">{rounded}%</span>
    </div>
  );
}
