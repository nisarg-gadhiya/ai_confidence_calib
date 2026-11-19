# Methodology I: Arithmetic Pipeline

The arithmetic pipeline answers numerical and mathematical questions such as GSM8K word problems [@cobbe2021] and produces a confidence for every step of the solution. It is the pipeline closest to the original project proposal: each step is scored by asking the model to *redo* that step several times from the same starting point, by asking a separate verifier whether the step is correct, and by reading the token probabilities of the redone steps. This chapter describes each stage, gives the formula for every signal, and explains how the signals are fused and how the trainable calibrator and the error-injection utility fit in. The flow is summarised in @fig:arith-flow.

![Arithmetic pipeline. Each step is resampled K times from a fixed prefix, verified, and scored; the answer confidence is the lowest step confidence.](arithmetic_pipeline.png){#fig:arith-flow}

## Step Generation {#sec:arith-generation}

A question is first answered once, deterministically (temperature 0), with a system prompt that asks the model to return a JSON object containing an ordered `steps` array and a `final_answer` string. Each step has an integer `step_number`, concise user-facing `text`, and a `step_type` chosen from a closed list: `arithmetic`, `unit_conversion`, `factual_recall`, `logical_inference`, `setup`, `conclusion` or `other`. The prompt asks for "brief, verifiable work rather than hidden chain-of-thought", so each step should be checkable on its own. The response is requested in JSON mode and parsed by `_parse_reasoning`, which rejects a response that has no step list.

Two design choices matter here. First, generation and scoring are separated: the steps that are shown to the user are produced once, greedily, and are never altered by the scoring stage. Confidence describes these exact steps. Second, step boundaries are produced by the model in a structured field rather than recovered from free text. The project proposal (FYP-1) identified step segmentation as a risk; structured output removes it for this pipeline. A regular-expression decomposer (`decompose_reasoning`, which recognises "Step N:" prefixes) remains in the code for free-text inputs and for the evaluation scripts.

## Prefix-Conditioned Next-Step Sampling {#sec:arith-sampling}

For every step $i$, the pipeline asks the model to continue the solution from the *fixed prefix* of steps $1, \dots, i-1$ and to produce exactly one next step. The request includes the question, the preceding steps and the number of the step to generate, and asks for a JSON object with a single `step_text` field. The model is sampled $K$ times in one call (`n = K`, temperature 0.8) with token log-probabilities and the five most likely alternatives at each position (`top_logprobs = 5`). $K$ is set per request (default 5, range 1–10).

This is the key mechanical difference from response-level self-consistency [@wang2023] and semantic uncertainty [@kuhn2023], which resample *whole answers* from the question. Resampling whole answers mixes the uncertainty of every step into one distribution. Resampling only the next step, given everything before it, isolates the uncertainty that the model has *at this point* of the chain: if the model reliably reproduces the same step from the same prefix, that step is stable; if the K continuations diverge, instability begins here. The proposal called this *prefix-conditioned resampling*; it is what allows a confidence profile to locate an error rather than merely detect one.

Note that the prefix is the model's own greedy steps, not a verified-correct prefix. If an earlier step is wrong, later continuations are conditioned on the error. This is intentional, because confidence should describe the chain the user actually sees, but it means that errors can propagate into the consistency of later steps (Section @sec:arith-limitations).

## Step Verification and Semantic Grouping {#sec:arith-verification}

The K continuations and the original step are then passed to an independent verifier call (temperature 0). Following the finding of Kadavath et al. [@kadavath2022] that self-evaluation improves when the model sees several of its own samples, the verifier is shown the question, the fixed preceding steps, the proposed step and the K candidate continuations, and is told to treat the candidates "as sample-conditioned evidence, not as ground truth". It returns:

- `p_true` in [0, 1]: the verifier's estimate that the proposed step is correct;
- `rationale`: a short explanation, stored and shown in the interface;
- `step_type`: the verifier's own classification of the step (this value, not the generator's, is used for fusion);
- `sample_cluster_ids`: one non-negative integer per candidate, equal for two candidates only when they "express the same next-step meaning", with an instruction to be conservative about merging.

The cluster ids implement semantic equivalence: two continuations that say the same thing in different words fall into the same cluster. Semantic entropy as published [@kuhn2023; @farquhar2024] uses a natural-language-inference model to test bidirectional entailment between whole answers. Calibra delegates the equivalence judgement to the verifier LLM because no separate NLI model is hosted, and because intermediate arithmetic steps are short and formulaic, which makes generic NLI less reliable at this granularity (a risk noted in the proposal). The client validates the ids: if the list is missing, has the wrong length or contains invalid values, it is discarded, and the step falls back to exact-match agreement (recorded as `consistency_method = exact_match_fallback`).

## Signals {#sec:arith-signals}

Five quantities are computed for each step $i$. Let the K continuations be $s_1, \dots, s_K$, partitioned by the verifier into clusters $C_1, \dots, C_M$.

**Verification score.** $V_i$ is the verifier's `p_true`, clamped to [0, 1].

**Consistency.** The share of continuations in the largest semantic cluster:

$$A_i = \frac{\max_{m} |C_m|}{K}$$ {#eq:consistency}

**Semantic entropy.** The entropy of the cluster distribution, normalised by its maximum so that it lies in [0, 1]:

$$H_i = -\frac{1}{\log K}\sum_{m=1}^{M} \frac{|C_m|}{K}\,\log\frac{|C_m|}{K}$$ {#eq:semantic-entropy}

$H_i = 0$ when all continuations agree and $H_i = 1$ when every continuation is in its own cluster. Because $A_i$ and $H_i$ are both functions of the same cluster sizes they are strongly related; in the GSM8K pilot their correlation is −0.991 (Chapter 14). $H_i$ is stored and used as a calibrator feature but not in the default fusion.

**Sample agreement.** The exact-match analogue of $A_i$: continuations are lower-cased and whitespace-normalised, and $E_i$ is the share of the most common string. It is always computed, both as a fallback and as a calibrator feature.

**Token statistics.** For each continuation $s_k$, the client locates the bytes of the `step_text` value inside the raw JSON output and keeps only the tokens that overlap that span, so that JSON syntax does not dilute the statistics. Over those tokens it computes the mean log-probability $\bar{\ell}_k$ and the mean normalised entropy of the top-5 alternatives at each position. With $q_{t,j}$ the renormalised probabilities of the five alternatives at token $t$:

$$h_t = -\frac{1}{\log 5}\sum_{j=1}^{5} q_{t,j}\log q_{t,j}$$ {#eq:token-entropy}

The step's token probability is the geometric-mean token probability averaged over samples, and its token entropy is the average of $h_t$:

$$T_i = \exp\!\left(\frac{1}{K}\sum_{k=1}^{K}\bar{\ell}_k\right)$$ {#eq:token-prob}

These statistics describe the model's certainty while *producing* step $i$ from the fixed prefix. They are the per-step, span-restricted version of the latent-information family of methods discussed in Chapter 2: the proposal's objection to response-level token statistics was that averaging over a whole answer dilutes the one uncertain step, and restricting the span to a single step removes that dilution.

@tab:arith-signals summarises the signals and where each is stored in the API response.

Table: Per-step signals of the arithmetic pipeline. {#tab:arith-signals}

| Signal | Symbol | Source | Range | Response field |
|---|---|---|---|---|
| Verification | $V_i$ | Verifier `p_true` | [0, 1] | `verification_score` |
| Consistency | $A_i$ | Largest semantic cluster share | [1/K, 1] | `consistency_score` |
| Semantic entropy | $H_i$ | Cluster distribution | [0, 1] | `semantic_entropy` |
| Sample agreement | $E_i$ | Exact-match share | [1/K, 1] | `sample_agreement_score` |
| Mean token log-probability | $\bar{\ell}$ | Continuation tokens in `step_text` | (−∞, 0] | `mean_token_logprob` |
| Token entropy | $h$ | Top-5 alternatives, normalised | [0, 1] | `token_entropy` |
| Step confidence | $c_i$ | Fusion or calibrator | [0, 1] | `fused_confidence` |

## Type-Adaptive Fusion {#sec:arith-fusion}

The signals are combined into a step confidence by a weighted mean whose weights depend on the step type assigned by the verifier:

$$c_i = \frac{w_V V_i + w_A A_i + w_T T_i}{w_V + w_A + w_T}$$ {#eq:arith-fusion}

When token statistics are unavailable for a step (for example when the span cannot be located), the token term and its weight are dropped and the remaining two weights are renormalised. The weights are listed in @tab:arith-weights and compared visually with the factual and logical weights in Chapter 10.

Table: Type-adaptive fusion weights (`backend/app/services/fusion_service.py`). {#tab:arith-weights}

| Step type | Verification $w_V$ | Consistency $w_A$ | Token probability $w_T$ |
|---|---|---|---|
| `arithmetic` (calculation) | 0.35 | 0.40 | 0.25 |
| `unit_conversion` | 0.40 | 0.35 | 0.25 |
| `factual_recall` | 0.55 | 0.25 | 0.20 |
| `logical_inference`, `setup`, `conclusion`, `other` | 0.50 | 0.30 | 0.20 |

The rationale follows the failure modes of each step type. A calculation step has one right result, so if the model is unsure of it, resampling will produce different numbers; consistency therefore gets the largest weight. A factual-recall step inside a calculation ("there are 60 minutes in an hour") is either known or not, and repeated sampling tends to reproduce a confidently held wrong fact, which is the known blind spot of consistency methods [@manakul2023]; the verifier's judgement is weighted more heavily. Setup, inference and conclusion steps are judged mainly by whether they follow from what came before, which is what the verifier is asked. These weights are a reasoned prior, not a fitted model. The response therefore labels the result `type_adaptive_weighted_proxy`, and the report never describes it as a calibrated probability.

## Answer Confidence and Error Localisation {#sec:arith-aggregation}

The answer confidence is the minimum step confidence, and the predicted error step is the step that attains it:

$$C_{\text{answer}} = \min_i c_i, \qquad \hat{\imath} = \arg\min_i c_i$$ {#eq:arith-answer}

The minimum encodes the principle stated in the proposal that "a chain is only as reliable as its weakest step": an arithmetic answer is wrong if any step that feeds it is wrong. It is conservative by design. A geometric mean, used by the factual and logical pipelines (Chapter 10), would let several strong steps compensate for a weak one, which is undesirable when every step feeds the final number.

## Trainable Step Calibrator {#sec:arith-xgboost}

The weighted proxy can be replaced by a learned model that predicts $P(\text{step correct})$ from the step's features. The calibrator is a gradient-boosted tree classifier, XGBoost [@chen2016], chosen because it handles a small tabular feature set, missing values (for example a step with no token statistics) and non-linear interactions such as "high verification but low consistency" without feature scaling. The feature vector (`calibration_features.py`) has 13 entries: the six numeric signals of @tab:arith-signals other than the fused confidence (verification, consistency, sample agreement, semantic entropy, mean token log-probability, token entropy), with missing values encoded as NaN so that the trees learn a default direction, plus a one-hot encoding of the seven step types.

The training script (`arithmetic/experiments/train_step_calibrator.py`) reads one JSON line per labelled step, of the form `{"question_id", "step_correct", "features"}`, and trains with the hyperparameters in @tab:xgb-params. The data are split by *question*, not by step, using a grouped shuffle split that keeps all steps of a question on the same side; up to 50 candidate splits are tried until both sides contain correct and incorrect steps. Grouping prevents the leak that would occur if steps of the same solution, which share a prefix and correlated signals, appeared in both training and test sets. The script reports ECE, MCE, Brier score, NLL, AUROC and reliability bins on the held-out questions (Chapter 10 defines each), and saves the model in XGBoost's JSON format.

Table: XGBoost step-calibrator hyperparameters (`arithmetic/fusion/xgboost_model.py`). {#tab:xgb-params}

| Parameter | Value | Purpose |
|---|---|---|
| `n_estimators` | 160 | Number of trees |
| `max_depth` | 3 | Shallow trees; limits overfitting on small data |
| `learning_rate` | 0.04 | Small shrinkage step |
| `subsample`, `colsample_bytree` | 0.85, 0.85 | Row and column subsampling |
| `reg_lambda` | 2.0 | L2 regularisation of leaf weights |
| Test fraction | 0.25 of questions | Grouped by `question_id` |
| Minimum data | 4 labelled steps, both classes in train and test | Enforced before training |

When `STEP_CALIBRATOR_PATH` points to a trained model, the API uses its prediction as the step confidence and labels the response `xgboost_step_calibrator`. No calibrator has been trained yet, because training requires step-level correctness labels, which the pilot data do not contain (Chapter 13); every arithmetic result in this report was therefore produced by the weighted proxy.

## Error-Injection Design {#sec:arith-error-injection}

Error localisation can only be evaluated against a known error position. GSM8K provides reference solutions, but a model's own solution rarely aligns step-for-step with the reference, and in the pilot every answer was correct. The project therefore includes a controlled error-injection utility (`arithmetic/data/error_injection.py`): given a list of steps, a 1-based step number and a non-zero integer `delta`, it finds the *last* number in the chosen step, adds `delta` to it (preserving decimals and removing thousands separators), and returns the corrupted chain together with the true error step. For example, the step "5 × 8 = 40" injected with `delta = 1` becomes "5 × 8 = 41", with `true_error_step` set to that step.

The intended experiment is to inject an error into one step of an otherwise correct chain, score the corrupted chain with the pipeline, and test whether the lowest-confidence step is the injected one (Top-1) or among the two lowest (Top-2), using the localisation functions in `arithmetic/evaluation/localization.py`. Those functions evaluate only cases whose final answer is wrong and whose true error step is known, and report Top-1 and Top-2 accuracy over them. The utility and the metrics are implemented and unit-tested, but the injection experiment has not yet been run against the live pipeline, so no localisation accuracy is reported in Chapter 14.

## Worked Example {#sec:arith-example}

@fig:arith-signals-example shows the signals for every step of the first GSM8K test question in the pilot (stored in `arithmetic/experiments/results/gsm8k_pilot_5.json`). The verifier assigned `p_true` close to 1 to almost every step, while consistency varied between 0.2 and 1.0, so the fused confidence followed consistency closely. This pattern, a verifier that rarely doubts a correct-looking step and a consistency signal that carries most of the variation, holds across the pilot and is analysed in Chapter 14.

![Per-step signals for one GSM8K pilot question (left) and the mean of each signal across the factual and logical pilots (right).](signal_breakdown.png){#fig:arith-signals-example}

## Limitations of the Arithmetic Pipeline {#sec:arith-limitations}

- **Cost grows with chain length.** Each step costs one sampling call (returning K samples) and one verification call, so a six-step solution with K = 5 makes 13 model calls including generation (Chapter 13).
- **Errors propagate through the prefix.** Because sampling is conditioned on the model's own earlier steps, a wrong earlier step can make later continuations agree with each other on a wrong value, raising their consistency. The minimum aggregation limits the damage at answer level but not at step level.
- **The verifier is the same model family.** `p_true` comes from the same model that generated the step, so a shared blind spot is not caught [@kadavath2022]. In the pilot, verification scores averaged 0.98 and varied little.
- **Weights are not fitted.** The type-adaptive weights encode reasoning about failure modes, not evidence; fitting them, or training the XGBoost calibrator, requires labelled steps.
- **No hidden-state signal.** The hosted model exposes token log-probabilities but not hidden states, so the hidden-state features in the original design could not be implemented.
