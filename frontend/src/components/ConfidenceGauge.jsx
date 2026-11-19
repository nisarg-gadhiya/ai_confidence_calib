import { useEffect, useState } from "react";
import { confidenceLevel } from "../lib/normalize";

// Semicircle gauge. Arc length animates from 0 to the value on mount.
export default function ConfidenceGauge({ value, size = 200 }) {
  const [shown, setShown] = useState(0);
  const valid = typeof value === "number" && Number.isFinite(value);
  const target = valid ? Math.max(0, Math.min(1, value)) : 0;

  useEffect(() => {
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / 900);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(target * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  const level = confidenceLevel(value);
  const stroke = 14;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const arc = Math.PI * r;
  const path = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;

  return (
    <div
      className="gauge"
      role="meter"
      aria-label="Answer confidence"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={valid ? Math.round(target * 100) : undefined}
      style={{ width: size }}
    >
      <svg viewBox={`0 0 ${size} ${size / 2 + stroke}`} width={size} aria-hidden="true">
        <path d={path} className="gauge-track" strokeWidth={stroke} fill="none" strokeLinecap="round" />
        {/* threshold ticks at 50% and 75% */}
        {[0.5, 0.75].map((t) => {
          const a = Math.PI * (1 - t);
          const x1 = cx + (r - stroke) * Math.cos(a);
          const y1 = cy - (r - stroke) * Math.sin(a);
          const x2 = cx + (r + stroke) * Math.cos(a);
          const y2 = cy - (r + stroke) * Math.sin(a);
          return <line key={t} x1={x1} y1={y1} x2={x2} y2={y2} className="gauge-tick" />;
        })}
        {valid && (
          <path
            d={path}
            className={`gauge-fill tone-stroke-${level.tone}`}
            strokeWidth={stroke}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${arc * shown} ${arc}`}
          />
        )}
      </svg>
      <div className="gauge-readout">
        <strong>{valid ? `${Math.round(shown * 100)}%` : "—"}</strong>
        <span className={`tone-pill tone-${level.tone}`}>
          <span aria-hidden="true">{level.icon}</span> {level.label}
        </span>
      </div>
    </div>
  );
}
