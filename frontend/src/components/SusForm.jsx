/**
 * The System Usability Scale form: 10 statements, each answered 1 (Strongly disagree) to
 * 5 (Strongly agree), plus optional comments. Submit stays disabled until all 10 are answered,
 * and the unanswered ones are listed. The score is never calculated or shown here.
 */
import { useState } from 'react';

export default function SusForm({ questions, scale, initial, onSubmit, submitting = false, error = '' }) {
  const [answers, setAnswers] = useState(() =>
    Object.fromEntries(questions.map((_, i) => [`q${i + 1}`, initial?.[`q${i + 1}`] ?? null])));
  const [comments, setComments] = useState(initial?.comments ?? '');
  const missing = questions.map((_, i) => i + 1).filter((n) => answers[`q${n}`] === null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (missing.length) return;
    onSubmit({ ...answers, comments: comments.trim() || null });
  };

  return (
    <form className="sus-form" onSubmit={handleSubmit} noValidate>
      <ol className="sus-list">
        {questions.map((statement, i) => {
          const key = `q${i + 1}`;
          return (
            <li key={key} className="sus-item">
              <fieldset>
                <legend><span className="sus-item__number">{i + 1}.</span> {statement}</legend>
                <div className="sus-scale">
                  {scale.map((label, j) => (
                    <label key={label} className={`sus-option ${answers[key] === j + 1 ? 'sus-option--chosen' : ''}`}>
                      <input type="radio" name={key} value={j + 1} checked={answers[key] === j + 1}
                        onChange={() => setAnswers({ ...answers, [key]: j + 1 })} />
                      <span className="sus-option__value" aria-hidden="true">{j + 1}</span>
                      <span className="sus-option__label">{label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </li>
          );
        })}
      </ol>

      <div className="field">
        <label htmlFor="sus-comments">Comments (optional)</label>
        <textarea id="sus-comments" rows={3} maxLength={1000} value={comments}
          onChange={(e) => setComments(e.target.value)} />
      </div>

      {missing.length > 0 && (
        <p className="muted" role="status">
          Please answer all 10 statements. Still to answer: {missing.join(', ')}.
        </p>
      )}
      {error && <div className="alert alert--error" role="alert">{error}</div>}
      <button type="submit" className="btn btn--primary" disabled={missing.length > 0 || submitting}>
        {submitting ? 'Sending…' : 'Submit feedback'}
      </button>
    </form>
  );
}
