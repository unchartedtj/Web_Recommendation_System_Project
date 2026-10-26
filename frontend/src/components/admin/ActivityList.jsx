/**
 * Activity log entries as a readable list: "12 Oct 14:05 · info@techcorp.co.ke · Application accepted".
 */
export function describeAction(action) {
  const [area, what] = action.split('.');
  const text = `${area} ${(what ?? '').replace(/_/g, ' ')}`.trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit' });
}

export function detailsText(details) {
  if (!details) return '';
  return Object.entries(details)
    .filter(([, v]) => v !== null && v !== undefined && typeof v !== 'object')
    .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
    .join(' · ');
}

export default function ActivityList({ items }) {
  if (!items.length) return <p className="muted">No activity yet.</p>;
  return (
    <ul className="activity-list">
      {items.map((a) => (
        <li key={a.log_id}>
          <span className="muted small">{formatDateTime(a.created_at)}</span>
          <strong>{describeAction(a.action)}</strong>
          <span className="small">{a.actor ? a.actor.email : 'System'}</span>
          {detailsText(a.details) && <span className="muted small">{detailsText(a.details)}</span>}
        </li>
      ))}
    </ul>
  );
}
