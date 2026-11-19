# System Architecture

This chapter describes how Calibra is put together: the components and their responsibilities, the path a question takes from the browser to a stored calibration record, the gateway that decides which reasoning pipeline handles a question, the services shared by all pipelines, the persistence format, and the models that the system calls. The pipelines themselves are described in detail in Chapters 7 to 9; here they are treated as black boxes that accept a question and return a scored reasoning chain.

## Architectural Overview {#sec:arch-overview}

Calibra follows a layered client–server architecture (@fig:architecture). A single-page web application written in React sends questions to a Python FastAPI service. The service first asks a language model to classify the question as *arithmetic*, *factual* or *logical*, and then hands it to the pipeline built for that kind of reasoning. Each pipeline produces a chain of steps or atomic claims, measures several independent confidence signals for every step, fuses them into a step confidence, and aggregates the step confidences into an answer confidence. The API stores the complete result as a JSON record and returns it to the browser, where it is visualised.

![Overall architecture of Calibra. The gateway routes each question to one of three pipelines; all pipelines share the LLM client and the fusion and calibration stage, and every response is persisted.](architecture.png){#fig:architecture}

Three design decisions shape the architecture.

1. **Type-specific verification behind a common interface.** The three pipelines use very different evidence: token log-probabilities and resampling for arithmetic, web retrieval for factual claims, and an SMT solver for deduction. They nevertheless return the same kind of object, a list of steps each carrying a confidence and the signals behind it, so the API, the store and the frontend need no pipeline-specific logic beyond presentation.
2. **Step granularity everywhere.** The unit that is scored, stored and displayed is the reasoning step (or atomic claim), not the whole answer. Answer-level confidence is always derived from the step scores, never estimated separately (@fig:step-vs-response).
3. **Transparency over compactness.** Every signal that contributes to a score is returned and stored alongside it, together with a label stating how the score was produced (for example `fixed_sigmoid_not_empirically_calibrated`). This allows the analysis in Chapter 14 to be computed from stored records alone, and prevents a heuristic score from being presented as a calibrated probability.

![Response-level confidence (top) versus the step-level confidence profile produced by Calibra (bottom).](step_vs_response.png){#fig:step-vs-response}

Two kinds of user interact with the system (@fig:usecase). An end user asks questions and inspects the answer, its confidence and the evidence behind it. A researcher or examiner browses the stored runs, loads the run store, runs the pilot experiments and computes the calibration metrics.

![Use cases of Calibra.](usecase.png){#fig:usecase}

## Components {#sec:components}

@tab:components lists the main components, where they live in the repository and what each is responsible for. The repository layout is shown in @fig:repo-structure.

Table: Main components of Calibra. {#tab:components}

| Component | Location | Responsibility |
|---|---|---|
| Frontend | `frontend/src/` | Ask view (question input, answer, gauge, charts, reasoning chain, raw JSON) and Analytics view (charts over stored runs, run history) |
| API application | `backend/app/main.py` | FastAPI app, CORS policy, router registration |
| Gateway routes | `backend/app/api/routes/gateway.py` | `POST /api/ask` (classify, route, persist) and `GET /api/runs` (read stored runs) |
| Gateway | `gateway/` | LLM question classifier (`classifier.py`), routing (`router.py`), classification prompt and schema |
| Arithmetic pipeline | `backend/app/api/routes/inference.py`, `arithmetic/` | Step generation, next-step sampling, verification, type-adaptive fusion, optional XGBoost calibrator, evaluation utilities |
| Factual pipeline | `factual/` | Answer generation, claim decomposition, web retrieval, source reliability, claim verification, fusion and calibration |
| Logical pipeline | `logical/` | Premise and rule extraction, Z3 solver, forward-chaining proof builder, step verification and fusion |
| LLM client | `backend/app/services/llm_service.py` | All calls to the OpenAI API: generation, continuations with log-probabilities, step verification, web search, claim assessment, classification |
| Consistency service | `backend/app/services/consistency_service.py` | Exact-match agreement and semantic-cluster agreement and entropy |
| Fusion and calibration services | `backend/app/services/fusion_service.py`, `calibration_service.py`, `calibration_features.py` | Type-adaptive weights, error-step prediction, XGBoost feature encoding and inference |
| Run store | `backend/app/services/calibration_store.py` | Append-only JSON store of every answered question |
| Configuration | `backend/app/core/config.py`, root `.env` | Model names, API key, number of consistency samples, calibrator path |
| Tests | `tests/` | 105 automated tests across all modules (Chapter 15) |

![Repository organisation. Each pipeline is a self-contained Python package; shared services live under the backend application.](repo_structure.png){#fig:repo-structure}

## Request Lifecycle {#sec:lifecycle}

@fig:sequence-ask traces a single question through the system. The numbered interactions are:

1. The user types a question in the Ask view and submits it (button or `Ctrl+Enter`). The slider beside the input sets the number of consistency samples (1–10, default 5).
2. The frontend sends `POST /api/ask` with a JSON body `{"question": ..., "num_consistency_samples": ...}`. Pydantic validates the body: the question must be a non-empty string and the sample count must lie between 1 and 10.
3. The route calls `route_question`, which first calls the classifier.
4. The classifier sends the question to the LLM with a structured-output JSON schema whose only field, `category`, is restricted to the three allowed values, at temperature 0.
5. The router dispatches to `run_inference` (arithmetic), `process_factual` or `process_logical`.
6. The pipeline makes its own LLM calls: generation, sampling of alternative steps, verification and, for factual questions, web search. It fuses the signals for each step and assembles the response.
7. The route passes the response to `save_calibration_run`, which appends a record to `backend/data/calibration_runs.json`.
8. The response is returned to the browser and rendered.

![Sequence of interactions for one `POST /api/ask` request.](sequence_ask.png){#fig:sequence-ask}

Errors are mapped to HTTP status codes at the route boundary. A `ValueError` raised during classification or routing (for example an empty question, or a category outside the allowed set) becomes HTTP 400 with the error message as `detail`. Any other exception in routing becomes HTTP 500 with the generic message "Question routing failed." If the answer was produced but the record cannot be written, the route returns HTTP 500 with a message saying so, so that a stored history never silently diverges from what users were shown. The frontend renders `detail` as an inline alert; validation errors returned as a list are joined into one readable message.

The second endpoint, `GET /api/runs`, returns the stored records unchanged. It is read-only and is used by the Analytics view. A third endpoint, `GET /api/health`, reports service status.

## Gateway Classifier and Router {#sec:gateway}

The gateway decides which pipeline answers a question. It is implemented as a single LLM call rather than a trained classifier, for two reasons: the three categories are defined by the *primary reasoning operation* a question needs, which is a semantic judgement that surface features capture poorly, and no labelled routing dataset existed at the start of the project.

The classification prompt (reproduced in Appendix C) defines the categories as follows:

- **Arithmetic**: the question primarily requires numerical or mathematical calculation (arithmetic, percentages, ratios, equations, word problems).
- **Logical**: the question primarily requires deduction from statements, conditions or rules supplied in the question itself.
- **Factual**: the question primarily asks for knowledge that can be retrieved or recalled (entities, dates, places, definitions, scientific or historical facts).

The prompt adds explicit tie-breaking rules: a question that contains numbers is not automatically arithmetic, and a mixed question is classified by its primary operation. The model is instructed not to answer, explain or give confidence. Its output is constrained by the OpenAI structured-output feature to the schema in @tab:classifier-schema, with `strict` mode enabled and additional properties disallowed, so a malformed category cannot reach the router. The flow is summarised in @fig:gateway-flow.

Table: Structured-output schema used by the gateway classifier (`gateway/schemas.py`). {#tab:classifier-schema}

| Field | Type | Allowed values | Notes |
|---|---|---|---|
| `category` | string (enum) | `arithmetic`, `logical`, `factual` | Only field; `additionalProperties: false`; temperature 0 |

![Gateway routing. Validation failures and unsupported categories are reported as HTTP 400.](gateway_flow.png){#fig:gateway-flow}

Routing is deliberately the only place where the three pipelines are distinguished. Adding a fourth reasoning type would require a new enum value, a new branch in `route_question`, a pipeline package that returns the common step structure, and a mapping in the run store; nothing else in the backend would change.

## Shared Services {#sec:shared-services}

### LLM client

All model access goes through one class, `LLMService` (`backend/app/services/llm_service.py`), which wraps the OpenAI Python SDK. Centralising access has three benefits: prompts and response validation live in one place; every call returns parsed, validated data or raises a `ValueError`; and tests can substitute a stub client without network access (Chapter 15). @tab:llm-methods lists its operations.

Table: Operations of the shared LLM client. {#tab:llm-methods}

| Method | Used by | Model call | Sampling | Output |
|---|---|---|---|---|
| `classify_question` | Gateway | Chat completion, JSON schema (strict) | T = 0, n = 1 | `category` |
| `generate_reasoning` | Arithmetic | Chat completion, JSON object | T = 0, n = 1 | Steps with type, final answer |
| `generate_factual_reasoning` | Factual | Chat completion, JSON object | T = 0, n = 1 | Factual steps, final answer |
| `generate_logical_reasoning` | Logical | Chat completion, JSON object | T = 0, n = 1 | Inference steps, final answer |
| `generate_step_continuations` | Arithmetic, logical | Chat completion, JSON object, log-probs | T = 0.8, n = K | K candidate next steps with token statistics |
| `verify_step` | Arithmetic, logical | Chat completion, JSON object | T = 0, n = 1 | `p_true`, rationale, step type, semantic cluster ids |
| `search_web` | Factual | Responses API with `web_search` tool | tool required | Up to 5 cited URLs with excerpts |
| `assess_factual_claim` | Factual | Chat completion, JSON object | T = 0, n = 1 | Confidence, essential flag, per-source verdicts |

Every JSON response is checked before use. For example, `verify_step` rejects a missing or non-numeric `p_true`, clamps it to [0, 1], and discards the semantic cluster ids unless there is exactly one non-negative integer per sample; in that case the consistency service falls back to exact-match agreement and the step records `consistency_method = exact_match_fallback`. `assess_factual_claim` discards verdicts for source identifiers that were not in the evidence it was given, and forces the confidence to 0 when no evidence was supplied.

### Consistency, fusion and calibration services

The consistency service turns a set of K sampled continuations into an agreement score and, when the verifier supplied cluster ids, a normalised semantic entropy (formulas in Chapter 7). The fusion service holds the type-adaptive weight table for arithmetic steps and the arg-min rule for predicting the error step. The calibration service loads an XGBoost model from `STEP_CALIBRATOR_PATH` when one is configured and returns `P(step correct)`; when no model is configured it returns nothing and the proxy confidence is used instead. These services are described in Chapter 10.

## Persistence: the Run Store {#sec:run-store}

Every successful answer is appended to `backend/data/calibration_runs.json`, a JSON array with one record per question. A plain file was chosen over a database for this stage of the project because the records are written once and read in bulk for analysis, the volume is small, and a single human-readable file is easy to inspect, version and share with the analysis scripts. Writes are protected by a process-wide lock and performed atomically: the new array is written to a temporary file which then replaces the original, so a crash during a write cannot leave a truncated store. Values that cannot be represented in strict JSON (such as `NaN`) are rejected at write time.

Each record has a fixed header and two views of the result (@fig:data-model):

- `pipeline_output`: the complete response returned to the user, in the pipeline's native shape. It allows any past answer to be re-rendered exactly as it was shown.
- `steps`: a flattened, pipeline-independent list of the scored units with their signals. For arithmetic these are reasoning steps; for factual and logical questions they are atomic claims, each carrying its step identifier. Factual claims also carry their sources (identifier, title, URL, domain).

![Data model of a stored calibration run.](data_model.png){#fig:data-model}

The category of a stored record is inferred from the shape of the response: a `reasoning` key indicates the arithmetic pipeline, a `rules` key the logical pipeline, and a `steps` key the factual pipeline. @tab:run-fields describes the header fields, and the listing below shows an abridged real record (a three-hop logical question answered on 19 November 2026).

Table: Header fields of a stored run. {#tab:run-fields}

| Field | Type | Meaning |
|---|---|---|
| `run_id` | UUID string | Unique identifier generated at write time |
| `created_at` | ISO-8601 timestamp (UTC) | Time the record was written |
| `category` | `arithmetic` / `factual` / `logical` | Pipeline that answered, inferred from the response shape |
| `question` | string | Question as submitted |
| `answer` | string | Final answer shown to the user |
| `confidence` | number in [0, 1] | Answer confidence (`final_answer_confidence` or `answer_confidence`) |
| `calibration_status` | string | How the confidence was produced, e.g. `type_adaptive_weighted_proxy` or `fixed_sigmoid_not_empirically_calibrated` |
| `pipeline_output` | object | Complete pipeline response |
| `steps` | array | Flattened per-step / per-claim signals |

```json
{
  "run_id": "ab94b91d-cfe0-41ab-a52c-a031e9a012d1",
  "created_at": "2026-11-19T17:24:05.044939+00:00",
  "category": "logical",
  "question": "All pilots are crew members. If someone is a crew member and
               someone is a safety officer then someone is an emergency
               coordinator. All emergency coordinators are certified
               operators. Niko is a pilot. Niko is a safety officer.
               Is Niko a certified operator?",
  "answer": "Yes. Niko is certified operator.",
  "confidence": 0.8816344711799424,
  "calibration_status": "fixed_sigmoid_not_empirically_calibrated",
  "steps": [
    { "step_id": 1, "text": "Niko is crew member.", "essential": false,
      "verification_verdict": "ENTAILED", "logical_validity_score": 1.0,
      "self_verification_score": 1.0, "consistency_score": 1.0,
      "calibrated_probability": 0.9002495108803148, "sample_count": 5 },
    { "step_id": 2, "text": "Niko is emergency coordinator.",
      "verification_verdict": "ENTAILED", "logical_validity_score": 1.0,
      "self_verification_score": 0.4, "consistency_score": 0.2,
      "calibrated_probability": 0.6601583597237574, "sample_count": 5 },
    { "step_id": 3, "text": "Niko is certified operator.", "essential": true,
      "verification_verdict": "ENTAILED", "logical_validity_score": 1.0,
      "self_verification_score": 1.0, "consistency_score": 0.8,
      "calibrated_probability": 0.8816344711799424, "sample_count": 5 }
  ],
  "pipeline_output": { "...": "full response, omitted" }
}
```

Two properties of this record are worth noting because they recur in the analysis. First, the answer confidence (0.882) equals the calibrated probability of the single *essential* claim, step 3, because answer confidence is a geometric mean over essential claims only. Second, step 2 receives the lowest confidence (0.660) even though the solver verified it, because only one of the five sampled continuations agreed with it (consistency 0.2) and the verifier gave it `p_true` = 0.4. Step 2 would therefore be flagged as the most likely error location despite being logically valid; Chapter 14 returns to this pattern.

## Deployment and Configuration {#sec:deployment}

The system runs locally as two processes (@fig:deployment): the Vite development server for the frontend (port 5173 by default) and Uvicorn serving the FastAPI application (port 8000). The backend accepts cross-origin requests from `localhost` and `127.0.0.1` on any port, so that the frontend keeps working when Vite moves to another port because 5173 is occupied; other origins are refused. The Z3 solver runs in-process. The only external dependency at run time is the OpenAI API, used for all model calls and for web search; the factual pipeline additionally fetches cited web pages directly.

![Run-time deployment on a development workstation.](deployment.png){#fig:deployment}

Configuration is read by Pydantic Settings from a `.env` file at the repository root. @tab:config lists the settings that affect behaviour.

Table: Configuration settings (`backend/app/core/config.py`). {#tab:config}

| Setting | Default | Effect |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Only `openai` is supported; any other value raises an error |
| `LLM_MODEL` | `gpt-4o-mini` | Model for classification, generation, sampling and verification |
| `LLM_API_KEY` | none | Required; requests fail with a clear error if missing |
| `FACTUAL_SEARCH_MODEL` | `gpt-4.1-mini` | Model used with the web-search tool |
| `CONSISTENCY_SAMPLES` | 5 | Default K for next-step sampling when a request does not set it |
| `FUSION_METHOD` | `weighted` | Fusion strategy for arithmetic steps |
| `STEP_CALIBRATOR_PATH` | none | Path to a trained XGBoost step calibrator; when unset the proxy is used and labelled as such |
| `FRONTEND_URL` | `http://localhost:5173` | Recorded for reference; CORS is configured in `main.py` |
| `DATABASE_URL` | `sqlite:///./ai_confidence.db` | Reserved for a future relational store; the run store currently uses JSON |

## Models Used and Why {#sec:models}

Calibra uses two hosted OpenAI models. `gpt-4o-mini` performs classification, step generation, next-step sampling and step verification. It was chosen because these operations are called many times per question (Chapter 13 gives the call counts by design), so per-call cost and latency dominate, and because the chat-completions API for this model exposes per-token log-probabilities, which the arithmetic pipeline needs for its token-level signal. `gpt-4.1-mini` is used only for web search in the factual pipeline, through the Responses API `web_search` tool, which returns cited URLs and the text spans they support.

Two constraints follow from using hosted models. First, hidden states and attention weights are not available, so the latent-state signals proposed in the original design (Chapter 5) could not be implemented; only output token statistics are used. Second, the models can change behind a fixed name, and web search results drift over time; Chapter 16 discusses the consequences for reproducibility. In return, the hosted models remove the need for GPU hardware, which allowed the project to concentrate on the verification and calibration logic that is its contribution.

## Summary

Calibra separates *what kind of reasoning a question needs* (the gateway) from *how each kind is verified* (three pipelines) and *how verification becomes confidence* (shared fusion and calibration). All pipelines return the same step-level structure, every signal is persisted, and every score carries a label stating how it was produced. The next three chapters open the three pipelines in turn.
