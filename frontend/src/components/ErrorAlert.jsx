export default function ErrorAlert({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="error-message" role="alert">
      <span className="error-icon" aria-hidden="true">!</span>
      <div>
        <strong>Something went wrong.</strong>
        <span>{message}</span>
      </div>
      {onRetry && (
        <button type="button" className="ghost-button" onClick={onRetry}>Retry</button>
      )}
    </div>
  );
}
