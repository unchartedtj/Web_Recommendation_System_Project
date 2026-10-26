/**
 * Give feedback (/feedback): the System Usability Scale questionnaire (test case TC10),
 * for students and industry partners. One response per person; sending it again updates it.
 * After submitting, the person is thanked. Their score is never shown to them.
 */
import { useCallback, useEffect, useState } from 'react';
import { fetchMySus, fetchSusQuestions, submitSus } from '../api/account.js';
import { parseApiError } from '../api/client.js';
import RoleLayout from '../components/RoleLayout.jsx';
import SusForm from '../components/SusForm.jsx';
import ErrorBanner from '../components/ui/ErrorBanner.jsx';
import LoadingSkeleton from '../components/ui/LoadingSkeleton.jsx';

export default function Feedback() {
  const [data, setData] = useState(null);       // { questions, scale, mine }
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [thanked, setThanked] = useState(false);

  const load = useCallback(() => {
    setLoadError('');
    Promise.all([fetchSusQuestions(), fetchMySus()])
      .then(([q, mine]) => setData({ ...q, mine }))
      .catch((err) => setLoadError(parseApiError(err).message));
  }, []);
  useEffect(load, [load]);

  const handleSubmit = async (answers) => {
    setSending(true);
    setError('');
    try {
      const res = await submitSus(answers);
      setData((d) => ({ ...d, mine: res.response }));
      setThanked(true);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <RoleLayout title="Give feedback">
      <p className="muted">
        Tell us how easy the WBL Placement System is to use. For each statement, choose how much
        you agree. It takes about 2 minutes.
      </p>
      <ErrorBanner message={loadError} onRetry={load} />
      {!data && !loadError && <LoadingSkeleton variant="lines" count={4} />}

      {thanked && (
        <div className="panel thank-you" role="status">
          <h2><span aria-hidden="true">🙏 </span>Thank you for your feedback!</h2>
          <p>Your answers have been saved. You can update them at any time.</p>
          <button type="button" className="btn btn--secondary" onClick={() => setThanked(false)}>
            Review my answers
          </button>
        </div>
      )}

      {data && !thanked && (
        <div className="panel">
          {data.mine && (
            <p className="muted small">You answered before. Your previous answers are filled in;
              submitting again updates them.</p>
          )}
          <SusForm key={data.mine?.updated_at ?? 'new'} questions={data.questions} scale={data.scale}
            initial={data.mine} onSubmit={handleSubmit} submitting={sending} error={error} />
        </div>
      )}
    </RoleLayout>
  );
}
