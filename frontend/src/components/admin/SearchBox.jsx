/**
 * A search input that waits until the user stops typing (300 ms) before searching.
 */
import { useEffect, useState } from 'react';

export default function SearchBox({ id, label = 'Search', value, onSearch, placeholder }) {
  const [text, setText] = useState(value ?? '');
  useEffect(() => { setText(value ?? ''); }, [value]);
  useEffect(() => {
    if (text === (value ?? '')) return undefined;
    const timer = setTimeout(() => onSearch(text.trim()), 300);
    return () => clearTimeout(timer);
  }, [text]);   // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} type="search" value={text} placeholder={placeholder}
        onChange={(e) => setText(e.target.value)} />
    </div>
  );
}
