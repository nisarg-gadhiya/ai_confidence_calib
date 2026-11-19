# Sources of every number in the report

All metrics are produced by `report/scripts/compute_metrics.py` (run in the project venv) and written to
`report/results/metrics.json` plus the CSV tables in this folder. Paths below are JSON paths inside
`metrics.json` unless another file is named. Raw inputs:

- `logical/experiments/results/logical_pilot.json` (RuleTaker pilot)
- `factual/experiments/results/factual_test.json` (TriviaQA pilot)
- `arithmetic/experiments/results/gsm8k_pilot_5.json` (GSM8K pilot)
- `backend/data/calibration_runs.json` (stored application runs)
- the test suite (`tests/`), run by the same script

## Arithmetic (GSM8K) — Chapters 1, 7, 13, 14

| Number in report | Source |
|---|---|
| 5 questions selected / completed | `arithmetic.questions_selected`, `arithmetic.questions_completed` |
| 5/5 correct; answers 18, 3, 70,000, 540, 20 | `arithmetic.calibration.accuracy`; `arithmetic_questions.csv` (`gold_answer`, `predicted_answer`) |
| Mean answer confidence 0.619 (range 0.599–0.624) | `arithmetic.calibration.mean_confidence`; `arithmetic.calibration.reliability_bins`; `arithmetic_questions.csv` |
| ECE 0.381, MCE 0.401, Brier 0.146, NLL 0.480, AUROC undefined | `arithmetic.calibration.{ece_10bin, mce_10bin, brier, nll, auroc, auroc_note}` |
| 32 steps; 3–13 per question; mean 6.4 | `arithmetic.steps_per_question` |
| Step types 22 / 4 / 3 / 2 / 1 | `arithmetic.step_types` |
| Signal statistics (verification 0.984 etc., Table 14.2) | `arithmetic.signals_step_level` |
| Correlations −0.991, −0.923, 0.943, 0.121, 0.517 | `arithmetic.signal_correlations_step_level` |
| 2 steps (6%) exact-match fallback | `arithmetic.consistency_method` |
| Fused confidence by type 0.846 / 0.783 / 0.702 | `arithmetic.fused_confidence_by_step_type` |
| Flagged step relative position 0.58 | `arithmetic.flagged_step_relative_position.mean` |
| Step 1 of example chain = 0.60 (Figure 14.4) | `gsm8k_pilot_5.json` → `results[*].reasoning_steps[0].fused_confidence` of the plotted question |
| 13.8 calls per question by design | 1 + 2 × `arithmetic.steps_per_question.mean` (design formula, Chapter 13) |
| Confidence by position 0.70 → 0.96 | `cross_pipeline.confidence_by_step_position.arithmetic` |

## Factual (TriviaQA) — Chapters 1, 8, 13, 14

| Number in report | Source |
|---|---|
| 100 selected, 40 completed | `factual.questions_selected`, `factual.questions_completed` |
| 28/40 (70%) correct by alias proxy | `factual.calibration.{positives, n, accuracy}`; label rule `factual.correctness_label` |
| Mean confidence 0.676; correct 0.668; wrong 0.694 | `factual.calibration.{mean_confidence, mean_conf_correct, mean_conf_wrong}` |
| ECE 0.238, MCE 0.602, Brier 0.261, NLL 0.724, AUROC 0.516 | `factual.calibration.*` |
| Reliability bins (0.85 → 0.71 with 17 questions; 0.76 → 0.40; 0.27 → 0.75) | `factual.calibration.reliability_bins` |
| 118 claims; 2–6 per answer; mean 2.95 | `factual.claims_total`, `factual.claims_per_answer` |
| Verdicts 70 / 3 / 45 | `factual.claim_verdicts` |
| 83 instruction-like claims in 40 answers; verdicts 47 / 33 / 3 | `factual.instruction_like_claims` |
| Signal means 0.592 / 0.705 / 0.605; medians 0.8 / 1.0 / 0.78 | `factual.signals_claim_level` |
| Correlations −0.028 / −0.166 / −0.032 | `factual.signal_correlation_with_answer_correctness` |
| 160 sources, 73 domains, 1.36 per claim | `factual.reliability_recorded.n`, `factual.unique_domains`, `factual.sources_per_claim.mean` |
| 145 fetched / 15 citation excerpts (91% / 9%) | `factual.text_origin` |
| Top domains (encyclopedia.com 12, …) | `factual.top_domains` |
| Recorded status 16 KEEP / 144 DOWN_WEIGHT; mean reliability 0.563, median 0.52 | `factual.source_status_recorded`, `factual.reliability_recorded` |
| Current policy 35 KEEP / 125 DOWN_WEIGHT; mean 0.617; 10% → 22% kept | `factual.source_status_under_current_policy`, `factual.reliability_current_policy` |
| Tiers 84 / 40 / 15 / 13 / 3 / 2 / 2 / 1 | `factual.source_tiers_under_current_policy` |
| Flagged steps 17 / 14 / 8 / 1 | `factual_questions.csv` (`predicted_error_step`) |
| 6.9 calls per question by design | 1 + 2 × `factual.claims_per_answer.mean` |
| Confidence by position 0.67–0.75 | `cross_pipeline.confidence_by_step_position.factual` |

## Logical (RuleTaker) — Chapters 1, 9, 13, 14

| Number in report | Source |
|---|---|
| 100 selected, 44 completed, all `depth-1`, indices 0–108 | `logical.questions_selected`, `logical.questions_completed`; `logical_pilot.json` (`config`, `dataset_index`) |
| 29/44 (66%) correct as recorded | `logical.accuracy_pilot` |
| 33/44 (75%) after parser fix (offline) | `logical.accuracy_after_parser_fix_offline` |
| Confusion matrices (8/0/15, 0/8/13; 12/0/11, 0/11/10) | `logical.confusion_pilot`, `logical.confusion_after_fix` |
| All ENTAILED and CONTRADICTED correct (8/8, 8/8); UNKNOWN 13/28 | `logical.correct_by_pilot_verdict` |
| 11 remaining misses; 9 negated queries; all closed-world | `logical.remaining_misses_after_fix`, `logical.remaining_misses_negated_query`, `logical.remaining_misses_note` |
| Mean confidence 0.471; correct 0.477; wrong 0.459 | `logical.calibration_pilot.*` |
| ECE 0.282, MCE 0.510, Brier 0.284, NLL 0.761, AUROC 0.430 | `logical.calibration_pilot.*` |
| Confidence by verdict 0.738 / 0.399 / 0.415 | `logical.confidence_by_pilot_verdict` |
| Within UNKNOWN: AUROC 0.215; correct 0.365 vs wrong 0.459 | `logical.calibration_within_unknown_answers` |
| Signals 0.323 (median 0.1) / 0.332 (median 0.2) / 0.182; semantic entropy 0.847 (median 1.0, n = 42) | `logical.signals_essential_claim` |
| Correlations 0.339 / −0.207 / 0.137 | `logical.signal_correlation_with_correctness` |
| Proof lengths {1: 38, 2: 6} pilot; {1: 40, 2: 4} after fix; mean 1.14 | `logical.proof_length_pilot`, `logical.proof_length_after_fix` |
| No inconsistent knowledge base | `logical.inconsistency_detections` |
| 3.3 calls per question by design | 1 + 2 × 1.14 |
| Confidence by position 0.53 / 0.39 | `cross_pipeline.confidence_by_step_position.logical` |

## Stored application runs — Chapters 6, 8, 9, 14

| Number in report | Source |
|---|---|
| 29 runs: 17 factual, 8 logical, 4 arithmetic; 23 with full output; 15:28–17:24 UTC, 19 Nov 2026 | `stored_runs.{runs, by_category, with_pipeline_output, first, last}` |
| Mean confidence 0.824 / 0.581 / 0.658 | `stored_runs.confidence_by_category` |
| "Niko" example: 0.882, step 2 = 0.660, consistency 0.2, p_true 0.4 | `calibration_runs.json` run 29 (index 28) |
| Apollo 11 example: claims 0.888 / 0.900 / 0.900, answer 0.900, 5 sources | `calibration_runs.json` run 16 (index 15) |
| Capital of India ×4 at 0.89–0.90 | `calibration_runs.json` indices 7, 8, 10, 18 |
| LSTM vs GRU ×4 at 0.70, 0.71, 0.85, 0.89 | indices 1, 2, 3, 27 |
| Five unverifiable answers at 0.27, 0.70, 0.71, 0.83, 0.83 | indices 1, 2, 4, 5, 12 |
| "Is Anne red?" 0.601 ×3 (ENTAILED); 0.554 UNKNOWN with stray quote | indices 17, 23, 24; 16 |
| Screenshot runs | `report/scripts/screenshots.mjs` (`STORED`: indices 20, 14, 28) |

## Cross-pipeline — Chapter 14

| Number in report | Source |
|---|---|
| 200 steps/claims; correlations 0.83, 0.90, 0.47, 0.54, 0.76 | `steps_all_pipelines.csv`; `cross_pipeline.step_signal_correlation` |

## System — Chapters 1, 6, 12, 15, Appendix F

| Number in report | Source |
|---|---|
| 105 tests; 15.12 s (pytest), 18.8 s wall | `tests.total`, `tests.summary`, `tests.wall_seconds` |
| Tests per file 7 / 1 / 2 / 12 / 37 / 16 / 30 | `tests.per_file` |
| 22 reliability tiers; weights 0.30–0.97; ~300 named domains | `factual/retrieval/source_reliability.py` (`SOURCE_RELIABILITY_WEIGHTS`, `DOMAIN_TIERS`); Appendix E generated by `gen_appendices.py` |
| Fusion weights, sigmoid, thresholds, XGBoost hyperparameters | source files named in Table 10.3 |
| Library versions | project venv `pip list`; `frontend/node_modules/*/package.json` (Chapter 12) |
| Commit dates and messages; working-tree counts; repository statistics | `git log`, `git status`, `git ls-files` via `gen_appendices.py` (Appendix F) |
| Proposal date 18 August 2026 | `FYP-1.docx`, first line |

## Literature figures — Chapter 3

Numbers quoted from surveyed papers (for example the Brier-score gaps 0.002–0.134 of Dogah, the ECE values 0.080 and 0.078 of Lamb et al., the 75 models of Arad and Rosset) are taken from the papers themselves: the three PDFs in `docs/papers/` and the published abstracts of the other works, as cited.
