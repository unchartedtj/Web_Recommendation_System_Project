/**
 * "Transcript verification" on My Profile: upload your official transcript (PDF) so the WBL
 * office can check it against the marks you typed. Shows the status:
 *   none      → not uploaded yet
 *   pending   → waiting for the WBL office
 *   accepted  → verified: you can apply for internships
 *   rejected  → the office's reason, so you can fix your marks or upload again
 */
import { useRef, useState } from 'react';
import { openMyTranscript, uploadTranscript } from '../../api/student.js';
import { parseApiError } from '../../api/client.js';
import { formatDate } from '../../utils/deadline.js';

const STATUS = {
  pending: { label: 'Pending verification', className: 'verify-status--pending',
    text: 'The WBL office will compare your transcript with the marks you entered. You can apply for internships once they are accepted.' },
  accepted: { label: 'Marks verified', className: 'verify-status--accepted',
    text: 'Your marks have been checked against your transcript. You can apply for internships.' },
  rejected: { label: 'Marks rejected', className: 'verify-status--rejected',
    text: 'Correct your marks below and/or upload the right transcript, then it will be checked again.' },
};

export default function TranscriptSection({ transcript, onUploaded }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const look = transcript ? STATUS[transcript.status] : null;

  const choose = (e) => {
    const chosen = e.target.files?.[0] ?? null;
    setError('');
    setMessage('');
    if (chosen && chosen.type && chosen.type !== 'application/pdf') {
      setError('Please choose a PDF file.');
      setFile(null);
      return;
    }
    if (chosen && chosen.size > 5 * 1024 * 1024) {
      setError('The file is too large (maximum 5 MB).');
      setFile(null);
      return;
    }
    setFile(chosen);
  };

  const send = async () => {
    setBusy(true);
    setError('');
    try {
      const saved = await uploadTranscript(file);
      onUploaded(saved);
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      setMessage('Transcript uploaded. The WBL office will verify your marks.');
    } catch (err) {
      setError(parseApiError(err).fields?.file ?? parseApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const view = () => openMyTranscript().catch((err) => setError(parseApiError(err).message));

  return (
    <section className="panel transcript-section" aria-labelledby="transcript-title">
      <div className="transcript-section__head">
        <h2 id="transcript-title">Transcript verification</h2>
        <span className={`verify-status ${look ? look.className : 'verify-status--none'}`}>
          {look ? look.label : 'Not uploaded'}
        </span>
      </div>

      <p className="muted">
        {look ? look.text
          : 'Upload your official transcript (PDF). The WBL office checks it against the marks you '
            + 'enter below before you can apply for internships.'}
      </p>
      {transcript?.status === 'rejected' && transcript.review_reason && (
        <p className="alert alert--error"><strong>Reason:</strong> {transcript.review_reason}</p>
      )}
      {transcript && (
        <p className="small">
          Current file: <button type="button" className="link-button" onClick={view}>{transcript.original_name}</button>
          {' '}<span className="muted">(uploaded {formatDate(transcript.uploaded_at)})</span>
        </p>
      )}

      <div className="transcript-section__upload">
        <label htmlFor="transcript-file" className="small">
          {transcript ? 'Upload a new transcript (PDF, max 5 MB)' : 'Transcript (PDF, max 5 MB)'}
        </label>
        <div className="transcript-section__row">
          <input id="transcript-file" ref={fileRef} type="file" accept="application/pdf,.pdf" onChange={choose} />
          <button type="button" className="btn btn--primary btn--sm" disabled={!file || busy} onClick={send}>
            {busy ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      </div>
      {error && <p className="field__error" role="alert">{error}</p>}
      {message && <p className="alert alert--success" role="status">{message}</p>}
    </section>
  );
}
