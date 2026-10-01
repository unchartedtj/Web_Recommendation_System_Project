/**
 * Labelled input with an inline error message (from client or API validation).
 * Pass as="textarea" for multi-line text.
 *
 * Reused by every form (Login, Register, Post Opportunity), so all inputs look and
 * behave the same. Example:
 *   <FormField label="Email" name="email" value={...} onChange={...} error={errors.email} />
 *
 * `as: Tag = 'input'` renames the `as` prop to Tag (default 'input'), so <Tag> becomes
 * <input> or <textarea>. `...inputProps` collects every other prop (type, value,
 * onChange, placeholder, ...) and passes them all to that element.
 */
export default function FormField({ label, name, error, as: Tag = 'input', className = '', ...inputProps }) {
  // The error message gets an id so the input can point to it (aria-describedby),
  // which lets screen readers read the error aloud.
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
