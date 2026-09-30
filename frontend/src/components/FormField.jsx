/**
 * Labelled input with an inline error message (from client or API validation).
 * Pass as="textarea" for multi-line text.
 */
export default function FormField({ label, name, error, as: Tag = 'input', className = '', ...inputProps }) {
  const errorId = `${name}-error`;
  return (
    <div className={`field ${error ? 'field--invalid' : ''} ${className}`}>
      <label htmlFor={name}>{label}</label>
      <Tag
        id={name}
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        {...inputProps}
      />
      {error && (
        <p className="field__error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}
