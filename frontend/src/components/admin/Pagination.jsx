/**
 * "Page 2 of 5" with Previous / Next buttons, for the paginated admin lists.
 */
export default function Pagination({ page, pages, total, onPage }) {
  if (!total) return null;
  return (
    <nav className="pagination" aria-label="Pages">
      <button type="button" className="btn btn--secondary btn--sm" disabled={page <= 1}
        onClick={() => onPage(page - 1)}>‹ Previous</button>
      <span className="muted small">Page {page} of {pages} · {total} total</span>
      <button type="button" className="btn btn--secondary btn--sm" disabled={page >= pages}
        onClick={() => onPage(page + 1)}>Next ›</button>
    </nav>
  );
}
