const EXAMPLES = [
  { category: "arithmetic", icon: "∑", text: "What is the derivative of 3x^2 + 5x?" },
  { category: "factual", icon: "◎", text: "What is the difference between LSTM and GRU?" },
  { category: "logical", icon: "⊢", text: "If all mammals are animals and a whale is a mammal, is a whale an animal?" },
];

export default function QuestionInput({ value, onChange, onSubmit, loading, samples, onSamplesChange }) {
  return (
    <form className="panel question-panel" onSubmit={onSubmit}>
      <div className="question-head">
        <h2 id="question-title">Your question</h2>
        <span className="kbd-hint"><kbd>Ctrl</kbd> + <kbd>Enter</kbd> to send</span>
      </div>
      <label className="visually-hidden" htmlFor="question">Enter your question</label>
      <textarea
        id="question"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onSubmit(e);
        }}
        placeholder="Ask anything: a calculation, a fact, or a logic puzzle…"
        rows={4}
        required
      />

      <div className="example-row">
        <span>Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.category}
            type="button"
            className="example-chip"
            style={{ "--cat": `var(--series-${ex.category === "arithmetic" ? 1 : ex.category === "factual" ? 2 : 3})` }}
            onClick={() => onChange(ex.text)}
            disabled={loading}
          >
            <span aria-hidden="true">{ex.icon}</span> {ex.text}
          </button>
        ))}
      </div>

      <div className="form-footer">
        <label className="samples-control">
          <span>Consistency samples <strong>{samples}</strong></span>
          <input
            type="range"
            min={1}
            max={10}
            value={samples}
            onChange={(e) => onSamplesChange(Number(e.target.value))}
            disabled={loading}
          />
        </label>
        <button type="submit" className="primary-button" disabled={loading || !value.trim()}>
          {loading ? (<><span className="spinner" aria-hidden="true" />Thinking</>) : (<>Get answer <span aria-hidden="true">→</span></>)}
        </button>
      </div>
    </form>
  );
}
