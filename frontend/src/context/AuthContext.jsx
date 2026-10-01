/**
 * Holds the logged-in user and JWT for the whole app.
 * Both are kept in localStorage so a page refresh doesn't log the user out.
 *
 * What is a "context"? Normally data is passed from parent to child component as props.
 * A context makes a value available to EVERY component inside <AuthProvider> (see main.jsx)
 * without passing it down by hand. Any component can call useAuth() to get
 * { user, token, isAuthenticated, login, logout }.
 *
 * localStorage = a small key/value store in the browser that survives page reloads.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as authApi from '../api/auth.js';
import { TOKEN_KEY, USER_KEY } from '../api/client.js';

const AuthContext = createContext(null);

/** Read the saved user from localStorage (stored as JSON text); null if missing or broken. */
function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  // Passing a FUNCTION to useState means "compute the starting value once, on first render".
  // So after a page refresh, we start already logged in if a token was saved.
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => (localStorage.getItem(TOKEN_KEY) ? readStoredUser() : null));

  // useCallback keeps the same function object between renders (a small performance detail).
  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password);      // throws if the login fails
    // Save to the browser so a refresh keeps us logged in...
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    // ...and to React state so the UI updates immediately.
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    // Forget everything; ProtectedRoute will then redirect to /login.
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  // On app load, confirm the stored token is still valid and refresh the user details.
  // A 401 here is handled by the axios interceptor, which clears the session.
  // useEffect runs code AFTER the component appears on screen; the [] at the end means
  // "only once", not after every re-render.
  useEffect(() => {
    if (!token) return;
    authApi
      .fetchMe()
      .then((fresh) => {
        localStorage.setItem(USER_KEY, JSON.stringify(fresh));
        setUser(fresh);
      })
      .catch(() => {});   // errors are already handled by the axios interceptor
    // Only needed once per page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The object every useAuth() caller receives. useMemo rebuilds it only when one of
  // the listed values changes, so components don't re-render for no reason.
  const value = useMemo(
    () => ({ user, token, isAuthenticated: Boolean(token && user), login, logout }),
    [user, token, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** The hook components call: const { user, logout } = useAuth(); */
export function useAuth() {
  const ctx = useContext(AuthContext);
  // A clear error if someone forgets to wrap the app in <AuthProvider>.
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
