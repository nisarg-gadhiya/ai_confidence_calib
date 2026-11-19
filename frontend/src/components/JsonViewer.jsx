import { useMemo, useState } from "react";

function matches(value, q) {
  if (!q) return false;
  if (value === null || typeof value !== "object") return String(value).toLowerCase().includes(q);
  return Object.entries(value).some(([k, v]) => k.toLowerCase().includes(q) || matches(v, q));
}

function Primitive({ value, q }) {
  let cls = "j-null";
  let text = "null";
  if (typeof value === "string") { cls = "j-str"; text = `"${value}"`; }
  else if (typeof value === "number") { cls = "j-num"; text = String(value); }
  else if (typeof value === "boolean") { cls = "j-bool"; text = String(value); }
  const hit = q && text.toLowerCase().includes(q);
  return <span className={`${cls} ${hit ? "j-hit" : ""}`}>{text}</span>;
}

function Node({ name, value, depth, q, expandAll, isLast }) {
  const isObj = value !== null && typeof value === "object";
  const isArr = Array.isArray(value);
  const [open, setOpen] = useState(expandAll ?? depth < 2);
  const forced = q ? matches(value, q) : null;
  const expanded = forced || open;
  const keyHit = q && name !== undefined && String(name).toLowerCase().includes(q);

  const label = name !== undefined && (
    <span className={`j-key ${keyHit ? "j-hit" : ""}`}>{typeof name === "number" ? name : `"${name}"`}<span className="j-punc">: </span></span>
  );
  const comma = isLast ? null : <span className="j-punc">,</span>;

  if (!isObj) {
    return <div className="j-line" style={{ paddingLeft: depth * 16 }}>{label}<Primitive value={value} q={q} />{comma}</div>;
  }

  const entries = isArr ? value.map((v, i) => [i, v]) : Object.entries(value);
  const [o, c] = isArr ? ["[", "]"] : ["{", "}"];

  return (
    <>
      <div className="j-line j-toggle" style={{ paddingLeft: depth * 16 }} onClick={() => setOpen(!expanded)}>
        <span className="j-caret" aria-hidden="true">{expanded ? "▾" : "▸"}</span>
        {label}
        <span className="j-punc">{o}</span>
        {!expanded && (
          <>
            <span className="j-summary">{isArr ? `${entries.length} items` : `${entries.length} keys`}</span>
            <span className="j-punc">{c}</span>{comma}
          </>
        )}
      </div>
      {expanded && (
        <>
          {entries.map(([k, v], i) => (
            <Node key={k} name={k} value={v} depth={depth + 1} q={q} expandAll={expandAll} isLast={i === entries.length - 1} />
          ))}
          <div className="j-line" style={{ paddingLeft: depth * 16 }}><span className="j-punc">{c}</span>{comma}</div>
        </>
      )}
    </>
  );
}

export default function JsonViewer({ data, title = "Raw JSON" }) {
  const [query, setQuery] = useState("");
  const [expandAll, setExpandAll] = useState(null);
  const [copied, setCopied] = useState(false);
  const [version, setVersion] = useState(0);
  const text = useMemo(() => JSON.stringify(data, null, 2), [data]);
  const q = query.trim().toLowerCase();

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  function setAll(v) {
    setExpandAll(v);
    setVersion((n) => n + 1);
  }

  return (
    <div className="json-viewer">
      <div className="json-toolbar">
        <strong>{title}</strong>
        <span className="json-size">{(text.length / 1024).toFixed(1)} KB</span>
        <input
          type="search"
          placeholder="Search keys or values…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search JSON"
        />
        <button type="button" className="ghost-button" onClick={() => setAll(true)}>Expand all</button>
        <button type="button" className="ghost-button" onClick={() => setAll(false)}>Collapse</button>
        <button type="button" className="ghost-button" onClick={copy}>{copied ? "✓ Copied" : "Copy"}</button>
      </div>
      <div className="json-body" key={version}>
        <Node value={data} depth={0} q={q} expandAll={expandAll} isLast />
      </div>
    </div>
  );
}
