import React, { useEffect, useState } from "react";
import { askQuestion, errorMessage } from "./services/api";
import { CATEGORY_META, normalizeResponse, pct } from "./lib/normalize";
import QuestionInput from "./components/QuestionInput";
import ErrorAlert from "./components/ErrorAlert";
import ResultView from "./components/ResultView";
import Dashboard from "./pages/Dashboard";
import "./App.css";

const STAGES = [
  "Routing your question to the right pipeline…",
  "Generating step-by-step reasoning…",
  "Sampling alternative reasoning paths…",
  "Verifying each step and claim…",
  "Calibrating the final confidence…",
];

function readTheme() {
  try {
    return localStorage.getItem("calibra-theme") || "system";
  } catch {
    return "system";
  }
}

function LoadingState() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 2600);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="panel loading-card" aria-live="polite">
      <div className="pulse-orb" aria-hidden="true"><span /><span /><span /></div>
      <div>
        <p className="loading-stage" key={stage}>{STAGES[stage]}</p>
        <div className="stage-dots" aria-hidden="true">
          {STAGES.map((_, i) => <span key={i} className={i <= stage ? "on" : ""} />)}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [view, setViewState] = useState(() =>
    window.location.hash === "#analytics" ? "analytics" : "ask",
  );
  const [theme, setTheme] = useState(readTheme);
  const [question, setQuestion] = useState("");
  const [samples, setSamples] = useState(5);
  const [history, setHistory] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function setView(next) {
    setViewState(next);
    window.history.replaceState(null, "", next === "analytics" ? "#analytics" : "#");
  }

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try { localStorage.setItem("calibra-theme", theme); } catch { /* storage unavailable */ }
  }, [theme]);

  async function handleSubmit(event) {
    event?.preventDefault();
    const submitted = question.trim();
    if (!submitted || loading) return;

    setLoading(true);
    setError("");
    setActiveId(null);
    try {
      const data = await askQuestion(submitted, samples);
      const entry = { id: Date.now(), result: normalizeResponse({ question: submitted, ...data }) };
      setHistory((h) => [entry, ...h].slice(0, 8));
      setActiveId(entry.id);
    } catch (e) {
      setError(errorMessage(e, "Unable to get an answer. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  const active = history.find((h) => h.id === activeId);
  const nextTheme = { system: "light", light: "dark", dark: "system" }[theme];
  const themeIcon = { system: "◐", light: "☀", dark: "☾" }[theme];

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Calibra home">
          <span className="brand-mark" aria-hidden="true">C</span>
          <span>Calibra</span>
        </a>
        <nav className="nav-tabs" aria-label="Views">
          <button type="button" className={view === "ask" ? "is-active" : ""} onClick={() => setView("ask")}>
            Ask
          </button>
          <button type="button" className={view === "analytics" ? "is-active" : ""} onClick={() => setView("analytics")}>
            Analytics
          </button>
        </nav>
        <button
          type="button"
          className="icon-button"
          onClick={() => setTheme(nextTheme)}
          title={`Theme: ${theme} (click for ${nextTheme})`}
          aria-label={`Theme: ${theme}. Switch to ${nextTheme}.`}
        >
          {themeIcon}
        </button>
      </header>

      {view === "ask" ? (
        <section className="workspace">
          <div className="intro">
            <p className="eyebrow">Ask · Understand · Verify</p>
            <h1>
              Answers that know <span className="grad-text">how sure they are.</span>
            </h1>
            <p className="intro-copy">
              Every question is routed to an arithmetic, factual, or logical
              reasoning pipeline. Each step is verified, sampled for
              consistency, and scored, so you can see exactly where the
              confidence comes from.
            </p>
          </div>

          <QuestionInput
            value={question}
            onChange={(v) => { setQuestion(v); setError(""); }}
            onSubmit={handleSubmit}
            loading={loading}
            samples={samples}
            onSamplesChange={setSamples}
          />

          {history.length > 0 && (
            <div className="history-row" aria-label="This session">
              <span>This session:</span>
              {history.map((h) => {
                const meta = CATEGORY_META[h.result.category] || CATEGORY_META.unknown;
                return (
                  <button
                    key={h.id}
                    type="button"
                    className={`history-chip ${h.id === activeId ? "is-active" : ""}`}
                    style={{ "--cat": meta.color }}
                    onClick={() => { setActiveId(h.id); setError(""); }}
                    title={h.result.question}
                  >
                    <span className="dot" />
                    <span className="history-q">{h.result.question}</span>
                    <strong>{pct(h.result.confidence)}</strong>
                  </button>
                );
              })}
            </div>
          )}

          <ErrorAlert message={error} onRetry={question.trim() ? handleSubmit : null} />

          {loading && <LoadingState />}

          {!loading && active && <ResultView key={active.id} result={active.result} />}

          {!loading && !active && !error && (
            <div className="feature-grid">
              {[
                ["∑", "Arithmetic", "Step-wise verification fused with sample agreement."],
                ["◎", "Factual", "Claims checked against retrieved web evidence."],
                ["⊢", "Logical", "Premises and rules checked by a solver."],
              ].map(([icon, title, text], i) => (
                <div key={title} className="feature" style={{ "--cat": `var(--series-${i + 1})` }}>
                  <span className="feature-icon" aria-hidden="true">{icon}</span>
                  <strong>{title}</strong>
                  <p>{text}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      ) : (
        <section className="workspace wide">
          <Dashboard />
        </section>
      )}
    </main>
  );
}
