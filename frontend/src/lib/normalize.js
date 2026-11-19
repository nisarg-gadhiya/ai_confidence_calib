// Turns any gateway response (arithmetic / logical / factual) or a stored
// calibration record into one shape the UI can render and chart.

const isNum = (v) => typeof v === "number" && Number.isFinite(v);
const num = (v) => (isNum(v) ? v : null);

export const CATEGORY_META = {
  arithmetic: { label: "Arithmetic", icon: "∑", color: "var(--series-1)" },
  factual: { label: "Factual", icon: "◎", color: "var(--series-2)" },
  logical: { label: "Logical", icon: "⊢", color: "var(--series-3)" },
  unknown: { label: "Other", icon: "?", color: "var(--muted)" },
};

export const VERDICT_META = {
  SUPPORT: { label: "Supported", icon: "✓", tone: "good" },
  CONTRADICT: { label: "Contradicted", icon: "✕", tone: "critical" },
  UNKNOWN: { label: "Unverified", icon: "?", tone: "warning" },
  // Logical solver verdicts
  ENTAILED: { label: "Entailed", icon: "✓", tone: "good" },
  CONTRADICTED: { label: "Contradicted", icon: "✕", tone: "critical" },
};

export function confidenceLevel(value) {
  if (!isNum(value)) return { label: "Unavailable", tone: "muted", icon: "–" };
  if (value >= 0.75) return { label: "High", tone: "good", icon: "▲" };
  if (value >= 0.5) return { label: "Moderate", tone: "warning", icon: "■" };
  return { label: "Low", tone: "critical", icon: "▼" };
}

export const pct = (v, digits = 0) =>
  isNum(v) ? `${(v * 100).toFixed(digits)}%` : "—";

export function detectCategory(data) {
  if (!data || typeof data !== "object") return "unknown";
  if ("reasoning" in data) return "arithmetic";
  if ("rules" in data || "premises" in data) return "logical";
  if ("steps" in data) return "factual";
  return "unknown";
}

function signal(key, label, value) {
  return { key, label, value: num(value) };
}

function arithmeticSteps(reasoning = []) {
  return reasoning.map((s) => ({
    id: String(s.step_number),
    stepNumber: s.step_number,
    text: s.step_text,
    type: s.step_type,
    confidence: num(s.fused_confidence),
    verdict: null,
    signals: [
      signal("verification", "Verification", s.verification_score),
      signal("consistency", "Consistency", s.consistency_score),
      signal("agreement", "Sample agreement", s.sample_agreement_score),
    ],
    rationale: s.verification_rationale || null,
    sources: [],
    meta: {
      "Semantic entropy": num(s.semantic_entropy),
      "Token entropy": num(s.token_entropy),
      "Mean token log-prob": num(s.mean_token_logprob),
      Samples: s.sample_count || null,
      Method:
        s.consistency_method === "exact_match_fallback"
          ? "Exact-match fallback"
          : null,
    },
  }));
}

function claimStep(step, claim, index, total, category) {
  const v = claim.verification || {};
  const third =
    category === "logical"
      ? signal("validity", "Logical validity", v.logical_validity_score)
      : signal("evidence", "Evidence", v.evidence_score);
  return {
    id: total > 1 ? `${step.step_id}.${index + 1}` : String(step.step_id),
    stepNumber: step.step_id,
    text: claim.text ?? claim.claim_text ?? step.text,
    type: step.reasoning_operation || v.reasoning_operation || (claim.essential ? "essential claim" : "claim"),
    confidence: num(claim.calibrated_probability),
    verdict: v.verdict || null,
    signals: [
      third,
      signal("self", "Self-verification", claim.self_verification_score),
      signal("consistency", "Consistency", claim.consistency_score),
    ],
    rationale: v.explanation || null,
    sources: (claim.sources || []).map((src) => ({
      id: src.source_id,
      title: src.title,
      url: src.url,
      domain: src.domain,
      reliability: num(src.reliability_score),
      status: src.status,
    })),
    premisesUsed: v.premises_used || step.premises_used || [],
    rulesUsed: v.rules_used || step.rules_used || [],
    meta: {
      "Semantic entropy": num(step.semantic_entropy),
      Samples: step.sample_count || null,
      Essential: claim.essential === false ? "No" : null,
    },
  };
}

function claimSteps(steps = [], category) {
  const out = [];
  for (const step of steps) {
    const claims = step.claims || [];
    if (!claims.length) {
      out.push({
        id: String(step.step_id),
        stepNumber: step.step_id,
        text: step.text,
        type: step.reasoning_operation || "step",
        confidence: null,
        verdict: null,
        signals: [],
        sources: [],
        meta: { Samples: step.sample_count || null },
      });
      continue;
    }
    claims.forEach((c, i) => out.push(claimStep(step, c, i, claims.length, category)));
  }
  return out;
}

// Stored records written before `pipeline_output` existed only carry flat steps.
function flatStoredSteps(steps = [], category) {
  if (category === "arithmetic") {
    return arithmeticSteps(
      steps.map((s) => ({
        step_number: s.step_id,
        step_text: s.text,
        step_type: s.step_type,
        verification_score: s.verification_score,
        consistency_score: s.consistency_score,
        sample_agreement_score: s.sample_agreement_score,
        fused_confidence: s.fused_confidence,
        sample_count: s.sample_count,
      })),
    );
  }
  const seen = {};
  steps.forEach((s) => { seen[s.step_id] = (seen[s.step_id] || 0) + 1; });
  const idx = {};
  return steps.map((s) => {
    idx[s.step_id] = (idx[s.step_id] || 0) + 1;
    return claimStep(
      { step_id: s.step_id, text: s.text, reasoning_operation: s.reasoning_operation, sample_count: s.sample_count },
      {
        text: s.text,
        essential: s.essential,
        verification: {
          verdict: s.verification_verdict,
          evidence_score: s.evidence_score,
          logical_validity_score: s.logical_validity_score,
        },
        self_verification_score: s.self_verification_score,
        consistency_score: s.consistency_score,
        calibrated_probability: s.calibrated_probability,
        sources: s.sources,
      },
      idx[s.step_id] - 1,
      seen[s.step_id],
      category,
    );
  });
}

function weakestStepId(steps) {
  let weakest = null;
  for (const s of steps) {
    if (s.confidence === null) continue;
    if (!weakest || s.confidence < weakest.confidence) weakest = s;
  }
  return weakest?.id ?? null;
}

/** Normalize a live gateway response. */
export function normalizeResponse(data) {
  const category = detectCategory(data);
  const steps =
    category === "arithmetic"
      ? arithmeticSteps(data.reasoning)
      : claimSteps(data.steps, category);
  const flagged = data.predicted_error_step;
  return {
    category,
    question: data.question,
    answer: data.final_answer,
    confidence: num(data.answer_confidence ?? data.final_answer_confidence),
    method: data.calibration_status || data.confidence_method || null,
    flaggedStep: flagged ?? null,
    weakestId: weakestStepId(steps),
    steps,
    logic:
      category === "logical"
        ? {
            premises: data.premises || [],
            rules: data.rules || [],
            contradictions: data.contradictions || [],
            unsupported: data.unsupported_premises || [],
            inconsistent: Boolean(data.inconsistency_detected),
          }
        : null,
    raw: data,
  };
}

/** Normalize a stored calibration record (from calibration_runs.json). */
export function normalizeRecord(record) {
  if (record.pipeline_output) {
    const n = normalizeResponse(record.pipeline_output);
    return { ...n, runId: record.run_id, createdAt: record.created_at, raw: record };
  }
  const category = record.category || "unknown";
  const steps = flatStoredSteps(record.steps, category);
  return {
    category,
    question: record.question,
    answer: record.answer,
    confidence: num(record.confidence),
    method: record.calibration_status,
    flaggedStep: null,
    weakestId: weakestStepId(steps),
    steps,
    logic: null,
    raw: record,
    runId: record.run_id,
    createdAt: record.created_at,
  };
}

export function prettyMethod(method) {
  if (!method) return null;
  return method.replace(/_/g, " ");
}
