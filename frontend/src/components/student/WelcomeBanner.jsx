/**
 * A dismissible welcome message at the top of the student dashboard, with a link that opens
 * the key WBL requirements in a pop-up. Once dismissed it stays hidden (remembered in this
 * browser's localStorage). While it's showing, it is the page's main heading.
 */
import { useState } from 'react';
import WblRequirements from '../WblRequirements.jsx';
import Modal from '../ui/Modal.jsx';

export const WELCOME_DISMISSED_KEY = 'wbl_welcome_dismissed';

function readDismissed() {
  try {
    return localStorage.getItem(WELCOME_DISMISSED_KEY) === '1';
  } catch {
    return false;          // storage blocked (e.g. private mode): just show the banner
  }
}

export default function WelcomeBanner({ firstName }) {
  const [dismissed, setDismissed] = useState(readDismissed);
  const [showRequirements, setShowRequirements] = useState(false);

  if (dismissed) return <h1>Welcome, {firstName}</h1>;

  const dismiss = () => {
    try { localStorage.setItem(WELCOME_DISMISSED_KEY, '1'); } catch { /* ignore */ }
    setDismissed(true);
  };

  return (
    <section className="welcome-banner" aria-labelledby="welcome-title">
      <div>
        <h1 id="welcome-title">Welcome, {firstName}</h1>
        <p>
          Your WBL placement is a key step between the classroom and your career. Complete your
          profile to see the placements that suit you best.
        </p>
        <button type="button" className="link-button" onClick={() => setShowRequirements(true)}>
          Learn about WBL requirements
        </button>
      </div>
      <button type="button" className="welcome-banner__close" onClick={dismiss}
        aria-label="Dismiss welcome message">
        <span aria-hidden="true">✕</span>
      </button>

      {showRequirements && (
        <Modal title="Key WBL requirements" onClose={() => setShowRequirements(false)} footer={(
          <button type="button" className="btn btn--primary" onClick={() => setShowRequirements(false)}>
            Got it
          </button>
        )}>
          <WblRequirements />
        </Modal>
      )}
    </section>
  );
}
