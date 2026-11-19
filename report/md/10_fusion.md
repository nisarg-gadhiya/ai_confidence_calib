# Signal Fusion, Calibration and Error Localisation

Chapters 7 to 9 described how each pipeline measures its signals. This chapter puts the three side by side: the common framework that turns signals into a step confidence, the two ways step confidences are aggregated into an answer confidence, how the weakest step is chosen as the predicted error location, what in the scoring is hand-set and what is fitted, and how calibration quality is measured.

## A Common Framework {#sec:fusion-framework}

Every pipeline computes, for each step or claim $i$, three kinds of signal (@tab:signal-families, @fig:fusion-flow):

- a **self-verification** signal $V_i$, the model's own judgement that the step is correct, obtained from a separate verification call that sees the step in context;
- a **consistency** signal $A_i$, the agreement among several independent views of the step;
- a **domain-evidence** signal $D_i$, obtained from a source of evidence suited to the reasoning type.

Table: The three signal families in each pipeline. {#tab:signal-families}

| Family | Arithmetic | Factual | Logical |
|---|---|---|---|
| Self-verification $V$ | Verifier `p_true` given K samples | Assessment confidence given evidence | Verifier `p_true` given K samples |
| Consistency $A$ | Largest semantic cluster share of K next-step samples | Agreement of per-source verdicts | Largest cluster share, scaled by contradiction penalty |
| Domain evidence $D$ | Token probability of the samples | Reliability- and relevance-weighted evidence score | Solver entailment (logical validity) |
| Fusion | Type-adaptive weights | 0.4 / 0.3 / 0.3 | 0.4 / 0.3 / 0.3 |
| Mapping to [0, 1] | none (proxy) or XGBoost | $\sigma(-1 + 3.2 f)$ | $\sigma(-1 + 3.2 f)$ |
| Answer confidence | minimum over steps | geometric mean of essential claims | geometric mean of essential claims |

![Common fusion and calibration flow shared by the three pipelines.](fusion_flow.png){#fig:fusion-flow}

The three families are complementary by design, and the literature identifies a blind spot for each one taken alone. Self-verification is weakest exactly where the model's knowledge is weakest, because the same gap that produced an error also hides it [@kadavath2022]. Consistency cannot detect a model that is consistently wrong [@manakul2023]. External evidence is only as good as its coverage of the claim. Combining them aims to cover each blind spot with another signal. In particular, the domain-evidence signal is the only one that does not come from the model being evaluated: it comes from the token distribution, from independent web sources, or from a theorem prover.

The fused score $f_i$ is a weighted mean, with the weights shown in @fig:fusion-weights. For arithmetic, the weights depend on the step type (Chapter 7); for factual and logical claims they are fixed at 0.4 for self-verification and 0.3 for each of the other two signals.

![Fusion weights: type-adaptive weights for arithmetic steps (left) and fixed weights for factual and logical claims (right).](fusion_weights.png){#fig:fusion-weights}

## From Fused Score to Probability {#sec:fusion-calibration}

A fused score is not a probability. A calibrated probability $p$ must satisfy the property that, among all steps given $p = 0.7$, about 70% are actually correct. Calibra handles this differently in the three pipelines, and it records which way was used in every response (@tab:calibration-status):

- **Arithmetic** offers a trainable XGBoost calibrator that predicts $P(\text{step correct})$ from the step's feature vector (Chapter 7). Until a model is trained, the fused score itself is used as a *proxy* and labelled as such.
- **Factual and logical** pipelines map the fused score through a fixed logistic function, $p = \sigma(-1 + 3.2 f)$ (@fig:sigmoid). The mapping is monotone, so it preserves the ranking of steps and therefore cannot change discrimination (AUROC); it only rescales confidence. Its parameters were set by hand: they keep a claim with no supporting signal ($f = 0$) at 0.269, place the 0.5 point at $f = 0.3125$, and cap a claim with perfect signals ($f = 1$) at 0.900.

![The fixed sigmoid mapping used by the factual and logical pipelines.](sigmoid_mapping.png){#fig:sigmoid}

Table: Calibration-status labels attached to every response. {#tab:calibration-status}

| Label | Pipeline | Meaning |
|---|---|---|
| `type_adaptive_weighted_proxy` | Arithmetic | Step confidence is the type-adaptive weighted mean; no fitted calibration |
| `xgboost_step_calibrator` | Arithmetic | Step confidence predicted by a trained XGBoost model |
| `fixed_sigmoid_not_empirically_calibrated` | Factual, logical | Fused score mapped through the hand-set sigmoid |
| `not_applicable_inconsistent_premises` | Logical | Premises inconsistent; no confidence is given |

The labels serve an honesty requirement stated at the start of the project: a number that *looks* like a probability must not be presented as a calibrated probability unless it has been fitted to data. All results in this report come from the two unfitted methods (`type_adaptive_weighted_proxy` and `fixed_sigmoid_not_empirically_calibrated`); no XGBoost calibrator had been trained at the time of writing.

### Standard post-hoc calibrators

The fixed sigmoid has the same functional form as Platt scaling [@platt1999], $p = \sigma(a f + b)$, and could be fitted in the same way by minimising negative log-likelihood on labelled claims, giving $a$ and $b$ from data instead of the hand-set 3.2 and −1. Temperature scaling [@guo2017] is the special case $b = 0$ applied to logits, and isotonic regression [@zadrozny2002] replaces the sigmoid with any monotone step function. Each of these, like the current sigmoid, preserves ranking, so none of them can fix poor discrimination: if confidence does not rank correct answers above wrong ones, no monotone recalibration will. The XGBoost calibrator is different because it learns from the *individual signals*, so it can reweight them and change the ranking. This distinction matters for the results in Chapter 14, where the main problem is discrimination, not scale.

## Answer-Level Aggregation {#sec:fusion-aggregation}

Two aggregation rules are used, chosen to match how errors combine in each kind of reasoning:

- **Minimum (arithmetic).** Every step of a calculation feeds the final number, so one wrong step makes the answer wrong. The answer confidence is the lowest step confidence (@eq:arith-answer).
- **Geometric mean of essential claims (factual and logical).** A factual answer contains essential claims (needed to answer) and background claims (context). Only essential claims count, and their geometric mean (@eq:geomean) falls sharply when any one of them is weak but does not let a single slightly weaker claim decide everything. For a logical question with one target, the essential set has one member, and the answer confidence equals the target's probability.

## Error Localisation {#sec:fusion-localisation}

All three pipelines predict the error location as the step with the lowest confidence:

$$\hat{\imath} = \arg\min_i c_i$$ {#eq:argmin}

For factual questions the step probability is the minimum over its claims, so the flagged step is the step containing the weakest claim. The flagged step is returned as `predicted_error_step`, highlighted in red in the confidence chart, and marked "Predicted error step" in the reasoning chain (Chapter 11).

The proposal defined two metrics for localisation, implemented in `arithmetic/evaluation/localization.py`. Given cases whose final answer is wrong and whose true error step $e$ is known, with steps ranked by increasing confidence:

$$\mathrm{Top}\text{-}k = \frac{1}{N}\sum_{n=1}^{N} \mathbb{1}\left[e_n \in \text{the } k \text{ lowest-confidence steps of case } n\right], \quad k \in \{1, 2\}$$ {#eq:topk}

Top-2 is reported because an error often lowers the confidence of the step immediately after it as well as its own. The baseline that a localiser must beat is uniform attribution, whose expected Top-1 accuracy is $1/n$ for a chain of $n$ steps. Two features of the current design limit what the arg-min rule can do: it always flags exactly one step, even in a chain where every step is correct, and with a single-step chain it always flags that step. A threshold (flag only steps below a confidence level) would allow "no error"; it is listed as future work.

## Measuring Calibration {#sec:fusion-metrics}

Calibration quality is measured with the standard metrics defined in Chapter 2: expected and maximum calibration error over 10 equal-width bins (ECE, MCE) [@naeini2015; @guo2017], the Brier score [@brier1950], negative log-likelihood (NLL) and the area under the ROC curve (AUROC). They are implemented once, in `arithmetic/evaluation/metrics.py`, and used both by the XGBoost training script and by the analysis script that produced Chapter 14 (`report/scripts/compute_metrics.py`), so the two cannot disagree about definitions. Implementation details that affect the numbers are:

- bins are $[0, 0.1), [0.1, 0.2), \dots, [0.9, 1.0]$, with a confidence of exactly 1.0 placed in the last bin; empty bins are skipped in the sums;
- NLL clips probabilities to $[10^{-12}, 1 - 10^{-12}]$ to avoid infinite values;
- AUROC is computed with the Mann–Whitney rank statistic, giving tied scores their average rank (equivalent to counting a tied positive–negative pair as one half), and is undefined (reported as such, not as 0.5) when all examples have the same label.

The training script splits data by question, never by step, so that steps of one solution are not on both sides of the split (Chapter 7). It reports the metrics on held-out questions together with the reliability bins needed to draw a reliability diagram.

## What Is Hand-Set and What Is Fitted {#sec:fusion-handset}

@tab:handset summarises every numeric choice in the scoring and states whether it has been fitted to data. At the time of writing, none has.

Table: Numeric choices in the scoring and their status. {#tab:handset}

| Choice | Value | Where | Status |
|---|---|---|---|
| Type-adaptive arithmetic weights | @tab:arith-weights | `fusion_service.py` | Hand-set from failure-mode reasoning |
| Factual / logical weights | 0.4 / 0.3 / 0.3 | `factual/calibration/fusion.py` | Hand-set |
| Sigmoid slope and offset | 3.2, −1 | `factual/calibration/calibrator.py` | Hand-set; not fitted |
| Reliability tier weights | 0.30–0.97 | `source_reliability.py` | Hand-set policy |
| Filter thresholds | KEEP ≥ 0.75, DOWN_WEIGHT ≥ 0.45 | `reliability_filter.py` | Hand-set |
| Relevance threshold | 0.2 | `evidence_retrieval.py` | Hand-set |
| Sampling | K = 5, T = 0.8 | request / `llm_service.py` | Chosen for cost; K configurable 1–10 |
| XGBoost hyperparameters | @tab:xgb-params | `xgboost_model.py` | Fixed; model not yet trained |

The next step for the project (Chapter 17) is to replace the rows marked "hand-set" with values fitted to labelled steps: train the XGBoost calibrator for arithmetic, and fit the sigmoid (and, with enough data, the fusion weights) for factual and logical claims by minimising NLL.
