/**
 * A short success message in the corner that disappears after a few seconds.
 * role="status" makes screen readers announce it.
 */
import { useEffect } from 'react';

export default function Toast({ message, onDone, duration = 4000 }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(onDone, duration);
    return () => clearTimeout(timer);
  }, [message, onDone, duration]);

  if (!message) return null;
  return (
    <div className="toast" role="status">
      <span aria-hidden="true">✓ </span>{message}
    </div>
  );
}
