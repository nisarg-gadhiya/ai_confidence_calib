import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { fetchRuns, errorMessage } from "../services/api";
import { CATEGORY_META, VERDICT_META, normalizeRecord, pct } from "../lib/normalize";
import useThemeColors from "../lib/useThemeColors";
import ResultView from "../components/ResultView";
import ErrorAlert from "../components/ErrorAlert";
import { ChartTooltip } from "../components/ConfidenceChart";

const CATEGORIES = ["arithmetic", "factual", "logical"];
// Factual (SUPPORT/CONTRADICT) and logical (ENTAILED/CONTRADICTED) verdicts share outcomes.
const VERDICT_OUTCOMES = [
  ["good", { icon: "✓", label: "Supported / entailed", tone: "good" }],
  ["critical", { icon: "✕", label: "Contradicted", tone: "critical" }],
  ["warning", { icon: "?", label: "Unverified", tone: "warning" }],
];
const catColor = (c, cat) => c[`series-${CATEGORIES.indexOf(cat) + 1}`] || c.muted;
const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

function axis(c) {
  return { stroke: c.axis, tick: { fill: c.muted, fontSize: 12 }, tickLine: false };
}

function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {sub && <small>{sub}</small>}
    </div>
  );
}

export default function Dashboard() {
  const c = useThemeColors();
  const [records, setRecords] = useState(null);
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const fileRef = useRef(null);
  const detailRef = useRef(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchRuns();
      setRecords(Array.isArray(data) ? data : []);
      setSource("backend");
    } catch (e) {
      setError(`${errorMessage(e, "Could not load stored runs.")} You can also open calibration_runs.json directly.`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function onFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    file.text().then((text) => {
      try {
        const data = JSON.parse(text);
        if (!Array.isArray(data)) throw new Error("Expected a JSON array of runs.");
        setRecords(data);
        setSource(file.name);
        setError("");
        setSelected(null);
      } catch (err) {
        setError(`Could not read ${file.name}: ${err.message}`);
      }
    });
    e.target.value = "";
  }

  const runs = useMemo(
    () => (records || []).map((r, i) => ({ ...normalizeRecord(r), index: i })),
    [records],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return runs.filter(
      (r) => (filter === "all" || r.category === filter)
        && (!q || `${r.question} ${r.answer}`.toLowerCase().includes(q)),
    );
  }, [runs, filter, search]);

  const kpis = useMemo(() => {
    const conf = filtered.map((r) => r.confidence).filter((v) => v !== null);
    const verdicts = filtered.flatMap((r) => r.steps.map((s) => s.verdict).filter(Boolean));
    const supported = verdicts.filter((v) => v === "SUPPORT" || v === "ENTAILED").length;
    return {
      runs: filtered.length,
      avg: conf.length ? conf.reduce((a, b) => a + b, 0) / conf.length : null,
      steps: filtered.length ? filtered.reduce((a, r) => a + r.steps.length, 0) / filtered.length : null,
      support: verdicts.length ? supported / verdicts.length : null,
      claims: verdicts.length,
      low: conf.filter((v) => v < 0.5).length,
    };
  }, [filtered]);

  const shownCats = filter === "all" ? CATEGORIES : [filter];

  // Confidence over time: one scatter series per category.
  const timeline = useMemo(
    () => shownCats.map((cat) => ({
      cat,
      points: filtered
        .filter((r) => r.category === cat && r.confidence !== null)
        .map((r) => ({ t: new Date(r.createdAt).getTime(), confidence: r.confidence, question: r.question, index: r.index })),
    })),
    [filtered, filter],
  );

  // Histogram, stacked by category.
  const histogram = useMemo(() => {
    const bins = Array.from({ length: 10 }, (_, i) => ({ bin: `${i * 10}%`, range: `${i * 10}–${i * 10 + 10}%` }));
    for (const r of filtered) {
      if (r.confidence === null) continue;
      const i = Math.min(9, Math.floor(r.confidence * 10));
      bins[i][r.category] = (bins[i][r.category] || 0) + 1;
    }
    return bins;
  }, [filtered]);

  // Verdicts by category.
  const verdictRows = useMemo(
    () => shownCats.map((cat) => {
      const row = { cat: CATEGORY_META[cat].label };
      for (const r of filtered.filter((x) => x.category === cat)) {
        for (const s of r.steps) {
          const tone = s.verdict && VERDICT_META[s.verdict]?.tone;
          if (tone) row[tone] = (row[tone] || 0) + 1;
        }
      }
      return row;
    }).filter((row) => Object.keys(row).length > 1),
    [filtered, filter],
  );

  // Average step confidence by position in the chain.
  const byPosition = useMemo(() => {
    const acc = {};
    for (const r of filtered) {
      r.steps.forEach((s, i) => {
        if (s.confidence === null) return;
        const k = i + 1;
        acc[k] ??= { pos: k };
        acc[k][`${r.category}_sum`] = (acc[k][`${r.category}_sum`] || 0) + s.confidence;
        acc[k][`${r.category}_n`] = (acc[k][`${r.category}_n`] || 0) + 1;
      });
    }
    return Object.values(acc).map((row) => {
      const out = { pos: row.pos };
      for (const cat of CATEGORIES) if (row[`${cat}_n`]) out[cat] = row[`${cat}_sum`] / row[`${cat}_n`];
      return out;
    });
  }, [filtered]);

  function openRun(index) {
    setSelected(index);
    setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  const selectedRun = selected !== null ? runs.find((r) => r.index === selected) : null;
  const table = [...filtered].sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));

  return (
    <section className="dashboard">
      <div className="dash-head">
        <div>
          <p className="eyebrow">Calibration analytics</p>
          <h1 className="dash-title">Every run, visualized.</h1>
          <p className="intro-copy left">
            {records
              ? <>Showing <strong>{runs.length}</strong> stored runs from <code>{source === "backend" ? "backend/data/calibration_runs.json" : source}</code>.</>
              : loading ? "Loading stored calibration runs…" : "No runs loaded yet."}
          </p>
        </div>
        <div className="dash-actions">
          <button type="button" className="ghost-button" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "↻ Refresh"}
          </button>
          <button type="button" className="ghost-button" onClick={() => fileRef.current?.click()}>
            Open JSON file…
          </button>
          <input ref={fileRef} type="file" accept=".json,application/json" hidden onChange={onFile} />
        </div>
      </div>

      <ErrorAlert message={error} onRetry={load} />

      {loading && !records && (
        <div className="skeleton-grid">
          {Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton" />)}
        </div>
      )}

      {records && runs.length === 0 && (
        <div className="panel empty-card">
          <span className="empty-emoji" aria-hidden="true">📭</span>
          <p>No runs stored yet. Ask a question and it will show up here.</p>
        </div>
      )}

      {runs.length > 0 && (
        <>
          <div className="filter-row">
            <div className="segmented" role="group" aria-label="Filter by category">
              {["all", ...CATEGORIES].map((cat) => {
                const n = cat === "all" ? runs.length : runs.filter((r) => r.category === cat).length;
                return (
                  <button
                    key={cat}
                    type="button"
                    className={filter === cat ? "is-active" : ""}
                    onClick={() => setFilter(cat)}
                    disabled={n === 0}
                  >
                    {cat !== "all" && <span className="dot" style={{ background: catColor(c, cat) }} />}
                    {cat === "all" ? "All" : CATEGORY_META[cat].label}
                    <span className="count">{n}</span>
                  </button>
                );
              })}
            </div>
            <input
              type="search"
              className="search-input"
              placeholder="Search questions & answers…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="stat-row">
            <Stat label="Runs" value={kpis.runs} />
            <Stat label="Average confidence" value={pct(kpis.avg, 1)} />
            <Stat label="Steps per run" value={kpis.steps === null ? "—" : kpis.steps.toFixed(1)} />
            <Stat
              label="Claims supported"
              value={pct(kpis.support)}
              sub={kpis.claims ? `of ${kpis.claims} verified claims` : null}
            />
            <Stat label="Low-confidence runs" value={kpis.low} sub="below 50%" />
          </div>

          <div className="chart-grid">
            <div className="panel chart-card wide">
              <h3>Answer confidence over time</h3>
              <p className="chart-sub">Each dot is one run. Click a dot to inspect it.</p>
              <ResponsiveContainer width="100%" height={260}>
                <ScatterChart margin={{ top: 10, right: 12, bottom: 0, left: -12 }}>
                  <CartesianGrid stroke={c.grid} vertical={false} />
                  <XAxis
                    dataKey="t"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    scale="time"
                    tickFormatter={(t) => new Date(t).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                    {...axis(c)}
                  />
                  <YAxis dataKey="confidence" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => `${v * 100}%`} {...axis(c)} axisLine={false} />
                  <ZAxis range={[90, 90]} />
                  <Tooltip
                    cursor={{ stroke: c.axis, strokeDasharray: "3 3" }}
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const p = payload[0].payload;
                      return (
                        <div className="chart-tooltip">
                          <div className="chart-tooltip-title">{fmtDate(new Date(p.t).toISOString())}</div>
                          <p className="chart-tooltip-text">{p.question}</p>
                          <div className="chart-tooltip-row">
                            <span className="swatch" style={{ background: payload[0].payload.fill || payload[0].color }} />
                            <span>Confidence</span><strong>{pct(p.confidence, 1)}</strong>
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                  {timeline.map(({ cat, points }) => (
                    <Scatter
                      key={cat}
                      name={CATEGORY_META[cat].label}
                      data={points}
                      fill={catColor(c, cat)}
                      stroke={c.surface}
                      strokeWidth={2}
                      onClick={(p) => openRun(p.payload?.index ?? p.index)}
                      style={{ cursor: "pointer" }}
                    />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            <div className="panel chart-card">
              <h3>Confidence distribution</h3>
              <p className="chart-sub">How many runs fall in each confidence band.</p>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={histogram} margin={{ top: 10, right: 8, bottom: 0, left: -20 }} barCategoryGap="12%">
                  <CartesianGrid stroke={c.grid} vertical={false} />
                  <XAxis dataKey="bin" {...axis(c)} interval={0} />
                  <YAxis allowDecimals={false} {...axis(c)} axisLine={false} />
                  <Tooltip cursor={{ fill: c.grid, opacity: 0.5 }} content={(p) => <ChartTooltip {...p} label={p.payload?.[0]?.payload?.range} labelPrefix="Confidence " />} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                  {shownCats.map((cat, i) => (
                    <Bar
                      key={cat}
                      dataKey={cat}
                      name={CATEGORY_META[cat].label}
                      stackId="a"
                      fill={catColor(c, cat)}
                      stroke={c.surface}
                      strokeWidth={1}
                      radius={i === shownCats.length - 1 ? [4, 4, 0, 0] : 0}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="panel chart-card">
              <h3>Does confidence decay along the chain?</h3>
              <p className="chart-sub">Average step confidence by position in the reasoning chain.</p>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={byPosition} margin={{ top: 10, right: 12, bottom: 0, left: -12 }}>
                  <CartesianGrid stroke={c.grid} vertical={false} />
                  <XAxis dataKey="pos" tickFormatter={(v) => `S${v}`} {...axis(c)} />
                  <YAxis domain={[0, 1]} ticks={[0, 0.5, 1]} tickFormatter={(v) => `${v * 100}%`} {...axis(c)} axisLine={false} />
                  <Tooltip cursor={{ stroke: c.axis }} content={<ChartTooltip labelPrefix="Step " />} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                  {shownCats.map((cat) => (
                    <Line
                      key={cat}
                      type="monotone"
                      dataKey={cat}
                      name={CATEGORY_META[cat].label}
                      stroke={catColor(c, cat)}
                      strokeWidth={2}
                      dot={{ r: 4, strokeWidth: 2, stroke: c.surface, fill: catColor(c, cat) }}
                      activeDot={{ r: 6 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {verdictRows.length > 0 && (
              <div className="panel chart-card wide">
                <h3>Claim verification verdicts</h3>
                <p className="chart-sub">Outcome of checking each extracted claim against evidence or the rule base.</p>
                <ResponsiveContainer width="100%" height={60 + verdictRows.length * 44}>
                  <BarChart data={verdictRows} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 8 }} barCategoryGap="28%">
                    <CartesianGrid stroke={c.grid} horizontal={false} />
                    <XAxis type="number" allowDecimals={false} {...axis(c)} />
                    <YAxis type="category" dataKey="cat" width={80} {...axis(c)} axisLine={false} />
                    <Tooltip cursor={{ fill: c.grid, opacity: 0.5 }} content={<ChartTooltip />} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                    {VERDICT_OUTCOMES.map(([key, m], i, arr) => (
                      <Bar
                        key={key}
                        dataKey={key}
                        name={`${m.icon} ${m.label}`}
                        stackId="v"
                        fill={c[m.tone]}
                        stroke={c.surface}
                        strokeWidth={1}
                        radius={i === arr.length - 1 ? [0, 4, 4, 0] : 0}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="panel section-card">
            <h3>Run history <span className="muted">({table.length})</span></h3>
            <div className="table-wrap">
              <table className="run-table">
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Pipeline</th>
                    <th>Confidence</th>
                    <th className="num">Steps</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  {table.map((r) => {
                    const meta = CATEGORY_META[r.category] || CATEGORY_META.unknown;
                    return (
                      <tr
                        key={r.runId || r.index}
                        className={selected === r.index ? "is-selected" : ""}
                        onClick={() => openRun(r.index)}
                        tabIndex={0}
                        onKeyDown={(e) => e.key === "Enter" && openRun(r.index)}
                      >
                        <td className="q-cell">
                          <span>{r.question}</span>
                          <small>{r.answer}</small>
                        </td>
                        <td><span className="cat-pill" style={{ "--cat": meta.color }}>{meta.icon} {meta.label}</span></td>
                        <td>
                          <div className="table-meter">
                            <span className="mini-track"><span style={{ width: `${(r.confidence ?? 0) * 100}%` }} /></span>
                            <strong>{pct(r.confidence)}</strong>
                          </div>
                        </td>
                        <td className="num">{r.steps.length}</td>
                        <td className="muted nowrap">{fmtDate(r.createdAt)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div ref={detailRef}>
            {selectedRun && (
              <div className="run-detail">
                <div className="run-detail-head">
                  <h2>Run details</h2>
                  <button type="button" className="ghost-button" onClick={() => setSelected(null)}>✕ Close</button>
                </div>
                <ResultView key={selectedRun.index} result={selectedRun} />
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
