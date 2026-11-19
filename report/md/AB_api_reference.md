# API Reference

The backend exposes three endpoints under the `/api` prefix. Requests and responses are JSON. The server accepts cross-origin requests from `http://localhost` and `http://127.0.0.1` on any port.

## POST /api/ask

Classifies a question, routes it to the matching pipeline, stores the result and returns the pipeline's response unchanged. The request body is described in @tab:api-ask-request, and the error responses in @tab:api-errors.

Table: Request body of `POST /api/ask`. {#tab:api-ask-request}

| Field | Type | Required | Constraints | Default |
|---|---|---|---|---|
| `question` | string | yes | at least 1 character | — |
| `num_consistency_samples` | integer | no | 1 to 10 | 5 |

```json
{
  "question": "What is the derivative of 3x^2 + 5x?",
  "num_consistency_samples": 5
}
```

The response body depends on the pipeline that answered.

**Arithmetic.** Top-level fields `question`, `reasoning` (list of steps), `predicted_error_step`, `final_answer`, `final_answer_confidence` and `confidence_method`. Each step has `step_number`, `step_text`, `step_type`, `verification_score`, `consistency_score`, `sample_agreement_score`, `semantic_entropy`, `consistency_method`, `mean_token_logprob`, `token_entropy`, `fused_confidence`, `verification_rationale` and `sample_count`.

```json
{
  "question": "What is the derivative of 3x^2 + 5x?",
  "reasoning": [
    { "step_number": 1, "step_text": "...", "step_type": "setup",
      "verification_score": 1.0, "consistency_score": 0.6,
      "sample_agreement_score": 0.4, "semantic_entropy": 0.59,
      "consistency_method": "model_semantic_clusters",
      "mean_token_logprob": -0.27, "token_entropy": 0.18,
      "fused_confidence": 0.78, "verification_rationale": "...",
      "sample_count": 5 }
  ],
  "predicted_error_step": 1,
  "final_answer": "...",
  "final_answer_confidence": 0.62,
  "confidence_method": "type_adaptive_weighted_proxy"
}
```

**Factual.** Top-level fields `question`, `final_answer`, `steps`, `predicted_error_step`, `answer_confidence`, `answer_confidence_status` and `calibration_status`. Each step has `step_id`, `text` and `claims`; each claim has `claim_id`, `text`, `essential`, `verification` (`verdict`, `evidence_score`), `self_verification_score`, `consistency_score`, `calibrated_probability` and `sources` (each with `source_id`, `title`, `url`, `domain`, `text_origin`, `reliability_method`, `reliability_score`, `status`, `text`).

**Logical.** Top-level fields `question`, `final_answer`, `premises` (`premise_id`, `text`), `rules` (`rule_id`, `text`, `antecedents`, `consequents`, `disjunctive`), `steps`, `inconsistency_detected`, `contradictions`, `unsupported_premises`, `predicted_error_step`, `answer_confidence`, `answer_confidence_status` and `calibration_status`. Each step has `step_id`, `text`, `reasoning_operation`, `premises_used`, `rules_used`, `claims`, `consistency_method`, `semantic_entropy` and `sample_count`; each claim's `verification` has `verdict`, `logical_validity_score`, `premises_used`, `rules_used` and `reasoning_operation`.

Appendix D shows a complete response from each pipeline.

Table: Error responses of `POST /api/ask`. {#tab:api-errors}

| Status | When | Body |
|---|---|---|
| 422 | Request body fails validation (missing or empty question, samples outside 1–10) | `{"detail": [ {"loc": ..., "msg": ..., "type": ...} ]}` |
| 400 | Classification or routing raised a `ValueError` (for example an unsupported category) | `{"detail": "<message>"}` |
| 500 | Any other failure while answering | `{"detail": "Question routing failed."}` |
| 500 | Answer produced but the record could not be stored | `{"detail": "The question was processed, but calibration data could not be saved."}` |

## GET /api/runs

Returns the array of stored calibration runs exactly as stored in `backend/data/calibration_runs.json` (an empty array if the file does not exist). Each record has the fields described in @tab:run-fields. Returns HTTP 500 with `{"detail": "Stored calibration data could not be read."}` if the file cannot be read or does not contain an array.

## GET /api/health

Takes no parameters and returns `{"status": "ok"}` while the API is running. It is used as a liveness check.
