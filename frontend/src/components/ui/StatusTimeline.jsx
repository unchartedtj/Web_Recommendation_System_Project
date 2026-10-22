/**
 * A simple progress line: Applied → Shortlisted → Accepted / Rejected / Withdrawn.
 * Steps already reached are marked done; the last step shows the actual outcome.
 */
const FINAL_LABEL = { accepted: 'Accepted', rejected: 'Rejected', withdrawn: 'Withdrawn' };

export default function StatusTimeline({ status }) {
  const final = FINAL_LABEL[status];
  const steps = [
    { key: 'applied', label: 'Applied', done: true },
    { key: 'shortlisted', label: 'Shortlisted', done: status === 'shortlisted' || status === 'accepted' },
    { key: 'final', label: final ?? 'Decision', done: Boolean(final), outcome: status },
  ];
  return (
    <ol className="timeline" aria-label="Application progress">
      {steps.map((s) => (
        <li key={s.key}
          className={`timeline__step${s.done ? ' timeline__step--done' : ''}${s.key === 'final' && s.done ? ` timeline__step--${s.outcome}` : ''}`}>
          <span className="timeline__dot" aria-hidden="true" />
          {s.label}
          <span className="visually-hidden">{s.done ? ' (done)' : ' (not yet)'}</span>
        </li>
      ))}
    </ol>
  );
}
