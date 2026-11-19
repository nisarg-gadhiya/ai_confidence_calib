import StepConfidence from "./StepConfidence";

export default function ReasoningChain({ steps, flaggedId, selectedId, onSelect }) {
  if (!steps.length) return <p className="chart-empty">No reasoning steps were returned.</p>;
  return (
    <div className="timeline">
      {steps.map((step, i) => (
        <div className="timeline-item" key={step.id} style={{ animationDelay: `${i * 60}ms` }}>
          <StepConfidence
            step={step}
            flagged={step.id === flaggedId}
            selected={step.id === selectedId}
            onSelect={onSelect}
          />
        </div>
      ))}
    </div>
  );
}
