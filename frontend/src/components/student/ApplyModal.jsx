/**
 * The "Apply for this internship" dialog: the student's match, an optional motivation note
 * (max 500 characters, with a counter) and, when they're below an essential minimum mark,
 * a warning plus a required "I understand" checkbox.
 */
import { useState } from 'react';
import { applyToOpportunity } from '../../api/applications.js';
import { parseApiError } from '../../api/client.js';
import ConfirmDialog from '../ui/ConfirmDialog.jsx';
import MatchBar from '../ui/MatchBar.jsx';
import StatusBadge from '../ui/StatusBadge.jsx';

const NOTE_MAX = 500;

export default function ApplyModal({ opportunity, match, onApplied, onCancel }) {
  const [note, setNote] = useState('');
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const belowMinimum = Boolean(match && !match.meets_requirements);

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      const application = await applyToOpportunity({
        opportunity_id: opportunity.opportunity_id,
        motivation_note: note.trim() || null,
        acknowledge_below_minimum: belowMinimum && understood,
      });
      onApplied(application);
    } catch (err) {
      setError(parseApiError(err).message);
      setBusy(false);
    }
  };

  return (
    <ConfirmDialog title={`Apply: ${opportunity.title}`} confirmLabel="Confirm application"
      busy={busy} confirmDisabled={belowMinimum && !understood} error={error}
      onConfirm={submit} onCancel={onCancel}>
      {match && (
        <div className="apply-modal__match">
          <MatchBar percent={match.match_percent} label="Your match" />
          <StatusBadge eligible={match.meets_requirements} />
        </div>
      )}

      {belowMinimum && (
        <div className="alert alert--warn" role="note">
          <strong>You don&apos;t meet all the minimum requirements:</strong>
          <ul>
            {match.unmet_requirements.map((u) => (
              <li key={u.unit_id}>{u.unit}: you have {u.your_mark}, minimum {u.required}</li>
            ))}
          </ul>
          <label className="toggle">
            <input type="checkbox" checked={understood} required
              onChange={(e) => setUnderstood(e.target.checked)} />
            I understand I don&apos;t meet all minimum requirements
          </label>
        </div>
      )}

      <div className="field">
        <label htmlFor="apply-note">Motivation note (optional)</label>
        <textarea id="apply-note" rows={4} maxLength={NOTE_MAX} value={note}
          aria-describedby="note-count" onChange={(e) => setNote(e.target.value)}
          placeholder="Why are you a good fit for this internship?" />
        <small id="note-count" className="muted">{note.length}/{NOTE_MAX}</small>
      </div>
    </ConfirmDialog>
  );
}
