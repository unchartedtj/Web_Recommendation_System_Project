/**
 * A friendly error message with an optional "Try again" button.
 * Pass the message from parseApiError(), which turns technical errors into plain text.
 */
export default function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="alert alert--error error-banner" role="alert">
      <span><span aria-hidden="true">⚠ </span>{message}</span>
      {onRetry && (
        <button type="button" className="btn btn--secondary btn--sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
