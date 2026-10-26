/**
 * The account menu shown in every navbar: the user's name, then Give feedback (students and
 * partners) and Logout. (The Change password page is only used after an admin resets a
 * password: the user is sent there automatically.)
 * A real <button> with aria-expanded; Esc or clicking outside closes it.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { ROLES } from '../utils/roles.js';

export default function AccountMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => { if (!boxRef.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="account-menu" ref={boxRef}>
      <button type="button" className="account-menu__button" aria-haspopup="true" aria-expanded={open}
        onClick={() => setOpen(!open)}>
        <span aria-hidden="true">👤 </span>{user?.name ?? 'Account'} <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="account-menu__list" role="menu">
          {user?.role !== ROLES.ADMIN && (
            <Link role="menuitem" to="/feedback" onClick={() => setOpen(false)}>Give feedback</Link>
          )}
          <button type="button" role="menuitem" onClick={handleLogout}>Logout</button>
        </div>
      )}
    </div>
  );
}
