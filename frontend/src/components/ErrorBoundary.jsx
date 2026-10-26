/**
 * Catches any crash while drawing the page and shows "Something went wrong" instead of a
 * blank screen. (Error boundaries must be class components: React has no hook for this.)
 */
import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Visible in the browser's developer console, for debugging.
    console.error('Unexpected error in the page:', error, info?.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="auth-page">
        <div className="card status-page" role="alert">
          <p className="status-page__code" aria-hidden="true">⚠</p>
          <h1>Something went wrong</h1>
          <p className="muted">Sorry, this page ran into a problem. Reloading usually fixes it.</p>
          <button type="button" className="btn btn--primary" onClick={() => window.location.reload()}>
            Reload the page
          </button>
          {' '}
          <a className="btn btn--secondary" href="/">Go home</a>
        </div>
      </div>
    );
  }
}
