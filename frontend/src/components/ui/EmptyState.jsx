/**
 * A friendly "nothing here yet" panel: icon, title, a sentence, and an optional action
 * (a button or link passed in as `action`).
 */
export default function EmptyState({ icon = '📭', title, children, action }) {
  return (
    <div className="empty-state" role="status">
      <span className="empty-state__icon" aria-hidden="true">{icon}</span>
      <h2 className="empty-state__title">{title}</h2>
      {children && <p className="muted">{children}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
