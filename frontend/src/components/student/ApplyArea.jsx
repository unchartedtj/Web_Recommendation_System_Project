/**
 * The Apply area on the internship details page. What it shows depends on applyState():
 *   incomplete → "Complete your profile to apply" (link)
 *   can_apply  → "Apply" button (opens the Apply dialog)
 *   applied    → "Applied: <status>" (link to My Applications)
 *   closed     → "Applications closed"
 *   unverified → the WBL office must verify the student's marks (transcript) first
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
  } else if (state === 'unverified') {
    const status = data.transcript_status;
    content = (
      <>
        <p>
          {status === 'pending' && 'Your marks are waiting to be verified by the WBL office. You can apply once they are accepted.'}
          {status === 'rejected' && 'The WBL office could not verify your marks. See the reason on My Profile, fix them and upload again.'}
          {!status && 'Upload your transcript on My Profile. The WBL office must verify your marks before you can apply.'}
        </p>
        <Link className="btn btn--secondary" to="/student/profile">
          {status ? 'View verification status' : 'Upload transcript'}
        </Link>
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
