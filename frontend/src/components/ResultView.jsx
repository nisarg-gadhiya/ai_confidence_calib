import { useMemo, useState } from "react";
import ConfidenceGauge from "./ConfidenceGauge";
import ConfidenceChart, { SignalChart } from "./ConfidenceChart";
import ReasoningChain from "./ReasoningChain";
import LogicPanel from "./LogicPanel";
import JsonViewer from "./JsonViewer";
import { CATEGORY_META, VERDICT_META, pct, prettyMethod } from "../lib/normalize";

const TABS = [
  { key: "visual", label: "Visual breakdown" },
  { key: "json", label: "JSON" },
];

export default function ResultView({ result }) {
  const [tab, setTab] = useState("visual");
  const [selectedId, setSelectedId] = useState(null);
  const cat = CATEGORY_META[result.category] || CATEGORY_META.unknown;

  const flaggedId = useMemo(() => {
    if (result.flaggedStep !== null && result.flaggedStep !== undefined) {
      return result.steps.find((s) => s.stepNumber === result.flaggedStep)?.id ?? null;
    }
    return result.weakestId;
  }, [result]);

  const stats = useMemo(() => {
    const scored = result.steps.filter((s) => s.confidence !== null);
    const verdicts = {};
    for (const s of result.steps) if (s.verdict) verdicts[s.verdict] = (verdicts[s.verdict] || 0) + 1;
    const sources = new Set(result.steps.flatMap((s) => s.sources.map((x) => x.url || x.id)));
    return {
      steps: result.steps.length,
      min: scored.length ? Math.min(...scored.map((s) => s.confidence)) : null,
      verdicts,
      sources: sources.size,
    };
  }, [result]);

  function select(id) {
    setSelectedId((cur) => (cur === id ? null : id));
    document.getElementById(`step-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  const answer = typeof result.answer === "string" && result.answer.trim()
    ? result.answer
    : "No answer was returned for this question.";

  return (
    <section className="result" aria-live="polite">
      <div className="panel hero-card">
        <div className="hero-main">
          <div className="hero-tags">
            <span className="cat-pill" style={{ "--cat": cat.color }}>
              <span aria-hidden="true">{cat.icon}</span> {cat.label} pipeline
            </span>
            {result.method && <span className="chip subtle" title="Calibration method">{prettyMethod(result.method)}</span>}
          </div>
          {result.question && <p className="hero-question">{result.question}</p>}
          <p className="hero-answer">{answer}</p>
        </div>
        <div className="hero-gauge">
          <ConfidenceGauge value={result.confidence} />
          <span className="gauge-caption">Answer confidence</span>
        </div>
      </div>

      <div className="stat-row">
        <div className="stat"><span>Reasoning steps</span><strong>{stats.steps}</strong></div>
        <div className="stat"><span>Weakest step</span><strong>{pct(stats.min)}</strong></div>
        {Object.keys(stats.verdicts).length > 0 ? (
          <div className="stat">
            <span>Claim verdicts</span>
            <div className="verdict-bar" aria-label="Claim verdict distribution">
              {Object.entries(stats.verdicts).map(([v, n]) => {
                const m = VERDICT_META[v] || { tone: "muted", icon: "•", label: v };
                return (
                  <span key={v} className={`tone-pill tone-${m.tone}`} title={m.label}>
                    {m.icon} {n}
                  </span>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="stat"><span>Flagged step</span><strong>{flaggedId ? `S${flaggedId}` : "—"}</strong></div>
        )}
        <div className="stat"><span>Sources consulted</span><strong>{stats.sources || "—"}</strong></div>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            type="button"
            aria-selected={tab === t.key}
            className={`tab ${tab === t.key ? "is-active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "visual" ? (
        <>
          <div className="chart-grid">
            <div className="panel chart-card">
              <h3>Confidence by step</h3>
              <p className="chart-sub">
                Click a bar to jump to that step. Dashed line: answer confidence ({pct(result.confidence)}).
                {" "}Red: {result.flaggedStep != null ? "step the pipeline predicts is wrong" : "lowest-confidence step"}.
              </p>
              <ConfidenceChart
                steps={result.steps}
                flaggedId={flaggedId}
                flaggedLabel={result.flaggedStep != null ? "flagged" : "weakest"}
                answerConfidence={result.confidence}
                onSelect={select}
                selectedId={selectedId}
              />
            </div>
            <div className="panel chart-card">
              <h3>Signal breakdown</h3>
              <p className="chart-sub">The raw signals fused into each step’s confidence.</p>
              <SignalChart steps={result.steps} />
            </div>
          </div>

          <div className="panel section-card">
            <h3>Reasoning chain</h3>
            <ReasoningChain steps={result.steps} flaggedId={flaggedId} selectedId={selectedId} onSelect={select} />
          </div>

          {result.logic && (
            <div className="panel section-card">
              <h3>Knowledge base</h3>
              <LogicPanel logic={result.logic} steps={result.steps} />
            </div>
          )}
        </>
      ) : (
        <JsonViewer data={result.raw} title="Pipeline response" />
      )}
    </section>
  );
}
