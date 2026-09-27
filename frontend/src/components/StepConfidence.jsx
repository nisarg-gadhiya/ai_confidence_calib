export default function StepConfidence({
  step,
}) {

  return (

    <div>

      <strong>
        Step {step.step_number}
      </strong>

      <div>
        Type: {step.step_type}
      </div>

      <div>
        Verification:{" "}
        {step.verification_score.toFixed(2)}
      </div>

      <div>
        Consistency:{" "}
        {step.consistency_score.toFixed(2)}
      </div>

      <div>
        Sample agreement:{" "}
        {step.sample_agreement_score.toFixed(2)}
      </div>

      {step.semantic_entropy !== null && (
        <div>
          Semantic entropy:{" "}
          {step.semantic_entropy.toFixed(2)}
        </div>
      )}

      {step.consistency_method === "exact_match_fallback" && (
        <div>
          Consistency method: exact-match fallback
        </div>
      )}

      {step.mean_token_logprob !== null && (
        <div>
          Mean token log-probability:{" "}
          {step.mean_token_logprob.toFixed(2)}
        </div>
      )}

      {step.token_entropy !== null && (
        <div>
          Token entropy:{" "}
          {step.token_entropy.toFixed(2)}
        </div>
      )}

      <div>
        Confidence:{" "}
        {step.fused_confidence.toFixed(2)}
      </div>

      <p>
        {step.verification_rationale}
      </p>

    </div>
  );
}