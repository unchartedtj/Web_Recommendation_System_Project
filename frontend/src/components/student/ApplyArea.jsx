/**
 * The Apply area on the internship details page. What it shows depends on applyState():
 *   incomplete → "Complete your profile to apply" (link)
 *   can_apply  → "Apply" button (opens the Apply dialog)
 *   applied    → "Applied: <status>" (link to My Applications)
 *   closed     → "Applications closed"
 *   placed     → "You already have a confirmed placement"
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { applyState } from '../../utils/applyState.js';
import ApplicationStatusBadge from '../ui/ApplicationStatusBadge.jsx';
import ApplyModal from './ApplyModal.jsx';

export default function ApplyArea({ data, onApplied }) {
  const [open, setOpen] = useState(false);
  const state = applyState(data);

  let content;
  if (state === 'incomplete') {
    content = (
      <Link className="btn btn--primary" to="/student/profile">Complete your profile to apply</Link>
    );
  } else if (state === 'can_apply') {
    content = (
      <button type="button" className="btn btn--primary btn--block" onClick={() => setOpen(true)}>
        Apply
      </button>
    );
  } else if (state === 'applied') {
    content = (
      <>
        <p className="apply-area__status">
          Applied: <ApplicationStatusBadge status={data.my_application.status} />
        </p>
        <Link className="btn btn--secondary" to="/student/applications">View my applications</Link>
      </>
    );
  } else if (state === 'placed') {
    content = (
      <>
        <p><strong>You already have a confirmed placement.</strong></p>
        <Link className="btn btn--secondary" to="/student/applications">View my placement</Link>
      </>
    );
  } else {
    content = <p><strong>Applications closed</strong></p>;
  }

  return (
    <section className="panel apply-area" aria-labelledby="apply-heading" data-state={state}>
      <h2 id="apply-heading">Apply</h2>
      {content}
      {open && (
        <ApplyModal opportunity={data.opportunity} match={data.my_match}
          onCancel={() => setOpen(false)}
          onApplied={(application) => { setOpen(false); onApplied(application); }} />
      )}
    </section>
  );
}
