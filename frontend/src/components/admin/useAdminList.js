/**
 * Shared logic for the admin list pages.
 *
 * The filters live in the URL (?status=ongoing&page=2), so Back/Refresh keep them.
 *   const { params, setParam, data, error, reload } = useAdminList(fetchPlacements);
 *   setParam('status', 'ongoing')  → updates the URL, goes back to page 1, reloads
 */
import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { parseApiError } from '../../api/client.js';

export default function useAdminList(fetcher) {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = Object.fromEntries(searchParams.entries());
  const key = searchParams.toString();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  const reload = useCallback(() => {
    setError('');
    fetcher(Object.fromEntries(new URLSearchParams(key).entries()))
      .then(setData)
      .catch((err) => setError(parseApiError(err).message));
  }, [fetcher, key]);
  useEffect(() => { setData(null); reload(); }, [reload]);

  const setParam = (name, value) => {
    const next = new URLSearchParams(searchParams);
    if (value === '' || value === null || value === undefined) next.delete(name);
    else next.set(name, value);
    if (name !== 'page') next.delete('page');           // a new filter starts at page 1
    setSearchParams(next);
  };

  return { params, setParam, data, error, reload };
}
