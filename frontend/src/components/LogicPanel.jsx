export default function LogicPanel({ logic, steps }) {
  const used = new Set(steps.flatMap((s) => [...(s.premisesUsed || []), ...(s.rulesUsed || [])]));
  const { premises, rules, contradictions, unsupported, inconsistent } = logic;

  return (
    <div className="logic-panel">
      <div className="logic-status">
        {inconsistent ? (
          <span className="tone-pill tone-critical">✕ Inconsistency detected</span>
        ) : (
          <span className="tone-pill tone-good">✓ Premises consistent</span>
        )}
        <span className="chip">{premises.length} premises</span>
        <span className="chip">{rules.length} rules</span>
        {used.size > 0 && <span className="chip">{used.size} used in reasoning</span>}
      </div>

      <div className="logic-grid">
        <div>
          <h4>Premises</h4>
          <ul className="logic-list">
            {premises.map((p) => (
              <li key={p.premise_id} className={used.has(p.premise_id) ? "is-used" : ""}>
                <span className="mono">{p.premise_id}</span>
                <span>{p.text}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Rules</h4>
          <ul className="logic-list">
            {rules.map((r) => (
              <li key={r.rule_id} className={used.has(r.rule_id) ? "is-used" : ""}>
                <span className="mono">{r.rule_id}</span>
                <span>
                  {r.antecedents?.length ? (
                    <>
                      <em>{r.antecedents.join(r.disjunctive ? " or " : " and ")}</em>
                      <span className="arrow"> → </span>
                      {r.consequents.join(", ")}
                    </>
                  ) : r.text}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {(contradictions.length > 0 || unsupported.length > 0) && (
        <div className="logic-issues">
          {contradictions.map((c, i) => (
            <p key={`c${i}`} className="tone-text-critical">✕ {typeof c === "string" ? c : JSON.stringify(c)}</p>
          ))}
          {unsupported.map((u, i) => (
            <p key={`u${i}`} className="tone-text-warning">? Unsupported: {typeof u === "string" ? u : JSON.stringify(u)}</p>
          ))}
        </div>
      )}
    </div>
  );
}
