/**
 * Grey placeholder shapes shown while data loads, so the page never looks blank.
 *   variant="cards" → `count` card-shaped blocks     variant="lines" → `count` text lines
 * Screen readers just hear "Loading…".
 */
export default function LoadingSkeleton({ variant = 'cards', count = 3 }) {
  const items = Array.from({ length: count });
  return (
    <div className={`skeleton skeleton--${variant}`} role="status" aria-live="polite">
      <span className="visually-hidden">Loading…</span>
      {items.map((_, i) => (
        <div key={i} className="skeleton__block" aria-hidden="true">
          {variant === 'cards' && (
            <>
              <span className="skeleton__line skeleton__line--title" />
              <span className="skeleton__line" />
              <span className="skeleton__line skeleton__line--short" />
            </>
          )}
        </div>
      ))}
    </div>
  );
}
