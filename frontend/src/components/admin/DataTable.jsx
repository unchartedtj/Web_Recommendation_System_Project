/**
 * A simple table for admin lists. On phones each row becomes a stacked card
 * (the data-label on each cell supplies the column name; see .table in global.css).
 *
 *   columns: [{ key, label, render?: (row) => node, className? }]
 *   rows:    the items; rowKey picks each row's unique id.
 */
export default function DataTable({ columns, rows, rowKey, caption, onRowClick }) {
  return (
    <div className="panel panel--flush table-wrap">
      <table className="table admin-table">
        {caption && <caption className="visually-hidden">{caption}</caption>}
        <thead>
          <tr>{columns.map((c) => <th key={c.key} scope="col">{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className={onRowClick ? 'admin-table__clickable' : ''}
              onClick={onRowClick ? () => onRowClick(row) : undefined}>
              {columns.map((c) => (
                <td key={c.key} data-label={c.label} className={c.className}>
                  {c.render ? c.render(row) : row[c.key] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
