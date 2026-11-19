import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import useThemeColors from "../lib/useThemeColors";
import { pct } from "../lib/normalize";

export function ChartTooltip({ active, payload, label, labelPrefix = "", extra }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-title">{labelPrefix}{label}</div>
      {extra?.(payload[0].payload)}
      {payload.map((p) => (
        <div className="chart-tooltip-row" key={p.dataKey}>
          <span className="swatch" style={{ background: p.color || p.fill }} />
          <span>{p.name}</span>
          <strong>{typeof p.value === "number" && p.value <= 1 ? pct(p.value, 1) : p.value}</strong>
        </div>
      ))}
    </div>
  );
}

const axisProps = (c) => ({
  stroke: c.axis,
  tick: { fill: c.muted, fontSize: 12 },
  tickLine: false,
});

/** Per-step confidence, with the weakest / flagged step called out. */
export default function ConfidenceChart({ steps, flaggedId, flaggedLabel = "weakest", answerConfidence, onSelect, selectedId }) {
  const c = useThemeColors();
  const data = steps
    .filter((s) => s.confidence !== null)
    .map((s) => ({ id: s.id, name: `Step ${s.id}`, confidence: s.confidence, text: s.text }));
  if (!data.length) return <p className="chart-empty">No step-level confidence was returned.</p>;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 22, right: 8, bottom: 0, left: -12 }} barCategoryGap="22%">
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey="id" {...axisProps(c)} tickFormatter={(v) => `S${v}`} />
        <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => `${v * 100}%`} {...axisProps(c)} axisLine={false} />
        {typeof answerConfidence === "number" && (
          <ReferenceLine
            y={answerConfidence}
            stroke={c["text-2"]}
            strokeDasharray="4 4"
            strokeWidth={1.5}
          />
        )}
        <Tooltip
          cursor={{ fill: c.grid, opacity: 0.5 }}
          content={
            <ChartTooltip
              labelPrefix="Step "
              extra={(row) => <p className="chart-tooltip-text">{row.text}</p>}
            />
          }
        />
        <Bar
          dataKey="confidence"
          name="Confidence"
          radius={[4, 4, 0, 0]}
          maxBarSize={46}
          onClick={(row) => onSelect?.(row.id)}
          style={{ cursor: onSelect ? "pointer" : "default" }}
          isAnimationActive
        >
          {data.map((d) => (
            <Cell
              key={d.id}
              fill={d.id === flaggedId ? c.critical : c["series-1"]}
              fillOpacity={selectedId && selectedId !== d.id ? 0.45 : 1}
            />
          ))}
          <LabelList
            dataKey="id"
            position="top"
            content={({ x, y, width, value }) =>
              value === flaggedId ? (
                <text x={x + width / 2} y={y - 7} textAnchor="middle" fontSize={11} fontWeight={700} fill={c.text}>
                  ⚠ {flaggedLabel}
                </text>
              ) : null
            }
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Grouped bars: each confidence signal, per step. */
export function SignalChart({ steps }) {
  const c = useThemeColors();
  const withSignals = steps.filter((s) => s.signals.some((x) => x.value !== null));
  if (!withSignals.length) return <p className="chart-empty">No signal breakdown was returned.</p>;
  const keys = withSignals[0].signals.filter((s) =>
    withSignals.some((st) => st.signals.find((x) => x.key === s.key)?.value !== null),
  );
  const data = withSignals.map((s) => {
    const row = { id: s.id };
    for (const sig of s.signals) row[sig.key] = sig.value;
    return row;
  });
  const colors = [c["series-1"], c["series-2"], c["series-3"], c["series-4"]];

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 8, bottom: 0, left: -12 }} barGap={2} barCategoryGap="20%">
        <CartesianGrid vertical={false} stroke={c.grid} />
        <XAxis dataKey="id" {...axisProps(c)} tickFormatter={(v) => `S${v}`} />
        <YAxis domain={[0, 1]} ticks={[0, 0.5, 1]} tickFormatter={(v) => `${v * 100}%`} {...axisProps(c)} axisLine={false} />
        <Tooltip cursor={{ fill: c.grid, opacity: 0.5 }} content={<ChartTooltip labelPrefix="Step " />} />
        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: c["text-2"] }} />
        {keys.map((k, i) => (
          <Bar key={k.key} dataKey={k.key} name={k.label} fill={colors[i]} radius={[4, 4, 0, 0]} maxBarSize={18} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
