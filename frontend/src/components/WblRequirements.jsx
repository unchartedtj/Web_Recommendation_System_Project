/**
 * The key WBL attachment requirements (Strathmore SCES Attachment Guidelines).
 * Used on the landing page and in the student dashboard's pop-up.
 */
import { KEY_REQUIREMENTS } from '../content/wbl.js';

export default function WblRequirements() {
  return (
    <>
      <ul className="requirements-list">
        {KEY_REQUIREMENTS.map((r) => <li key={r}>{r}</li>)}
      </ul>
      <p className="muted small">Source: SCES Attachment Guidelines.</p>
    </>
  );
}
