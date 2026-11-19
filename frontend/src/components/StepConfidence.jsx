import { useState } from "react";
import { VERDICT_META, confidenceLevel, pct } from "../lib/normalize";

function Meter({ label, value }) {
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}</span>
        <strong>{pct(value)}</strong>
      </div>
      <div className="meter-track">
        <span style={{ width: `${(value ?? 0) * 100}%` }} />
      </div>
    </div>
  );
}

export default function StepConfidence({ step, flagged, selected, onSelect }) {
  const [open, setOpen] = useState(false);
  const level = confidenceLevel(step.confidence);
  const verdict = step.verdict ? VERDICT_META[step.verdict] || { label: step.verdict, icon: "•", tone: "muted" } : null;
  const meta = Object.entries(step.meta || {}).filter(([, v]) => v !== null && v !== undefined);
  const hasDetails =
    step.rationale || meta.length || step.sources.length ||
    step.premisesUsed?.length || step.rulesUsed?.length;

  return (
    <article
      id={`step-${step.id}`}
      className={`step-card ${flagged ? "is-flagged" : ""} ${selected ? "is-selected" : ""}`}
      onClick={() => onSelect?.(step.id)}
    >
      <div className={`step-node tone-ring-${level.tone}`} aria-hidden="true">{step.id}</div>

      <div className="step-body">
        <div className="step-top">
          <p className="step-text">{step.text}</p>
          <div className="step-score">
            <strong>{pct(step.confidence)}</strong>
            <span className={`tone-text-${level.tone}`}>{level.icon} {level.label}</span>
          </div>
        </div>

        <div className="chip-row">
          {step.type && <span className="chip">{step.type.replace(/_/g, " ")}</span>}
          {verdict && (
            <span className={`tone-pill tone-${verdict.tone}`}>
              <span aria-hidden="true">{verdict.icon}</span> {verdict.label}
            </span>
          )}
          {flagged && <span className="tone-pill tone-critical">⚠ Predicted error step</span>}
          {step.sources.length > 0 && <span className="chip">🔗 {step.sources.length} source{step.sources.length > 1 ? "s" : ""}</span>}
        </div>

        {step.signals.some((s) => s.value !== null) && (
          <div className="meter-grid">
            {step.signals.filter((s) => s.value !== null).map((s) => (
              <Meter key={s.key} label={s.label} value={s.value} />
            ))}
          </div>
        )}

        {hasDetails && (
          <button
            type="button"
            className="link-button"
            aria-expanded={open}
            onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
          >
            {open ? "Hide details" : "Show details"} <span aria-hidden="true">{open ? "▴" : "▾"}</span>
          </button>
        )}

        {open && (
          <div className="step-details" onClick={(e) => e.stopPropagation()}>
            {step.rationale && <p className="rationale">“{step.rationale}”</p>}
            {meta.length > 0 && (
              <dl className="meta-grid">
                {meta.map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{typeof v === "number" ? v.toFixed(3).replace(/\.?0+$/, "") : v}</dd>
                  </div>
                ))}
              </dl>
            )}
            {(step.premisesUsed?.length > 0 || step.rulesUsed?.length > 0) && (
              <div className="chip-row">
                {step.premisesUsed.map((p) => <span key={p} className="chip mono">{p}</span>)}
                {step.rulesUsed.map((r) => <span key={r} className="chip mono">{r}</span>)}
              </div>
            )}
            {step.sources.length > 0 && (
              <ul className="source-list">
                {step.sources.map((src, i) => (
                  <li key={`${src.id}-${i}`}>
                    <div>
                      {src.url ? (
                        <a href={src.url} target="_blank" rel="noreferrer">{src.domain || src.title}</a>
                      ) : (
                        <span>{src.domain || src.title}</span>
                      )}
                      {src.title && src.title !== src.url && <small>{src.title}</small>}
                    </div>
                    {src.reliability !== null && (
                      <span className="source-rel" title="Source reliability">
                        <span className="mini-track"><span style={{ width: `${src.reliability * 100}%` }} /></span>
                        {pct(src.reliability)}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
