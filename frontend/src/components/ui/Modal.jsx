/**
 * A pop-up dialog over the page. Esc or clicking the dark backdrop closes it, and focus
 * moves into it when it opens (for keyboard and screen-reader users).
 */
import { useEffect, useId, useRef } from 'react';

export default function Modal({ title, onClose, children, footer }) {
  const titleId = useId();
  const boxRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    // Focus the first input/button inside the dialog (once, when it opens).
    boxRef.current?.querySelector('input, textarea, select, button')?.focus();
    const onKey = (e) => { if (e.key === 'Escape') closeRef.current(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId} ref={boxRef}>
        <h2 id={titleId} className="modal__title">{title}</h2>
        <div className="modal__body">{children}</div>
        {footer && <div className="modal__footer">{footer}</div>}
      </div>
    </div>
  );
}
