/**
 * The opportunity's unit requirements next to the student's own marks:
 *   Unit | Essential/Desirable | Min mark | Your mark | ✓/✗
 * Without a profile (units have no my_mark), the last two columns are left out.
 * Each ✓/✗ also has text for screen readers ("met" / "not met").
 */
export default function UnitComparisonTable({ units, showMine = true }) {
  return (
    <table className="table unit-table">
      <thead>
        <tr>
          <th>Unit</th>
          <th>Importance</th>
          <th>Min mark</th>
          {showMine && <th>Your mark</th>}
          {showMine && <th aria-label="Requirement met?" />}
        </tr>
      </thead>
      <tbody>
        {units.map((u) => (
          <tr key={u.unit_id} className={showMine && !u.met ? 'unit-table__unmet' : ''}>
            <td data-label="Unit">{u.unit ?? u.unit_name}</td>
            <td data-label="Importance">
              {u.importance === 'essential' ? 'Essential' : 'Desirable'}
            </td>
            <td data-label="Min mark">{u.min_mark ?? '—'}</td>
            {showMine && <td data-label="Your mark">{u.my_mark ?? '—'}</td>}
            {showMine && (
              <td data-label="Met?" className={u.met ? 'tick' : 'cross'}>
                <span aria-hidden="true">{u.met ? '✓' : '✗'}</span>
                <span className="visually-hidden">{u.met ? 'met' : 'not met'}</span>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
