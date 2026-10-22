/**
 * "Are you sure?" dialog with Confirm and Cancel buttons. Extra inputs (e.g. a reason
 * or dates) can be passed as children. `error` shows an API error inside the dialog.
 */
import Modal from './Modal.jsx';

export default function ConfirmDialog({
  title, children, confirmLabel = 'Confirm', danger = false, busy = false,
  confirmDisabled = false, error = '', onConfirm, onCancel,
}) {
  return (
    <Modal title={title} onClose={onCancel} footer={(
      <>
        <button type="button" className="btn btn--secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="button" className={`btn ${danger ? 'btn--danger' : 'btn--primary'}`}
          onClick={onConfirm} disabled={busy || confirmDisabled}>
          {busy ? 'Please wait…' : confirmLabel}
        </button>
      </>
    )}>
      {children}
      {error && <div className="alert alert--error" role="alert">{error}</div>}
    </Modal>
  );
}
