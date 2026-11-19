# Experimental Setup

This chapter describes the pilot experiments whose results are analysed in Chapter 14: the datasets and how questions were selected, the models and sampling settings, how correctness was labelled, how each metric was computed, the cost of a question by design, and what was done to make the analysis reproducible. All three pilots are *pilots*: small runs intended to exercise each pipeline end to end on a public benchmark and to expose problems, not to establish final performance figures. Their sample sizes are reported beside every number.

## Datasets and Question Selection {#sec:setup-datasets}

@tab:datasets summarises the three benchmarks. Each pilot script streams its dataset from the Hugging Face Hub and selects questions deterministically, so the selection is reproducible.

Table: Pilot datasets and selection. {#tab:datasets}

| Pipeline | Dataset | Split / config | Selection rule | Selected | Completed |
|---|---|---|---|---|---|
| Arithmetic | GSM8K [@cobbe2021] (`openai/gsm8k`) | test | First 5 rows | 5 | 5 |
| Factual | TriviaQA [@joshi2017] (`mandarjoshi/trivia_qa`) | validation, `rc.nocontext` | First 100 rows of the streamed split | 100 | 40 |
| Logical | RuleTaker [@clark2020] (`tasksource/ruletaker`) | test, `default` | First 100 rows whose claim converts to a supported yes/no query | 100 | 44 |

**GSM8K** contains grade-school mathematics word problems with reference solutions whose last line has the form `#### answer`. The pilot used the first five test problems.

**TriviaQA** contains trivia questions with a reference answer and a list of accepted aliases. The `rc.nocontext` configuration provides the questions without evidence documents, which matches the factual pipeline's design of retrieving its own evidence from the web.

**RuleTaker** contains synthetic knowledge bases of facts and rules in controlled English, each with a statement to be judged and a label of *entailment* or *not entailment*. Because Calibra answers questions, each statement ("Anne is red.") was converted into a yes/no question ("Is Anne red?"). Rows whose statement does not match the pattern "X is [not] Y", or whose resulting target cannot be parsed into an atom, were skipped; the first 100 convertible rows were selected, and the 44 completed questions have test-split indices between 0 and 108. The question passed to the pipeline is the knowledge base followed by the question. All 44 completed questions come from the `depth-1` configuration of the benchmark, which means each requires at most one rule application under the dataset's own closed-world semantics.

### Incomplete runs

The factual and logical pilots stopped before completing all selected questions; the result files contain 40 of 100 and 44 of 100 questions respectively. The scripts save results after each question but cannot resume, and no log of the interruption was kept, so the reason is not recorded. Because questions were processed in order, the completed questions are the first 40 and the first 44 of each selection; there is no selection by outcome. Completing the pilots was deliberately not done for this report, to avoid further API spending; all results are therefore reported on the completed questions.

## Models and Settings {#sec:setup-models}

@tab:settings lists the models and sampling settings used in all three pilots.

Table: Model and sampling settings used in the pilots. {#tab:settings}

| Setting | Value |
|---|---|
| Generation, sampling, verification, claim assessment | `gpt-4o-mini` (OpenAI) |
| Web search (factual) | `gpt-4.1-mini` with `web_search` tool, context size *medium* |
| Generation temperature | 0 |
| Next-step sampling | K = 5 continuations, temperature 0.8, log-probabilities with top-5 alternatives |
| Verification and assessment temperature | 0 |
| Arithmetic calibration | `type_adaptive_weighted_proxy` (no trained calibrator) |
| Factual and logical calibration | `fixed_sigmoid_not_empirically_calibrated` |
| Sources kept per factual claim | up to 5; up to 2 page fetches |
| Solver timeout (logical) | 5 s per check |

The pilot scripts call the pipelines directly (`run_inference`, `process_factual`, `process_logical`) rather than through the gateway, because the dataset already determines the reasoning type. The gateway classifier was therefore not evaluated in the pilots. The runs were made on 19 November 2026 (the date of the commit that added the pilot results).

## Correctness Labels {#sec:setup-labels}

Answer correctness was determined differently for each dataset (@tab:labels).

Table: How answer correctness was labelled. {#tab:labels}

| Pipeline | Label | Rule |
|---|---|---|
| Arithmetic | Exact numeric match | The last number in the model's final answer equals the number after `####` in the reference solution |
| Factual | Alias found in reasoning (proxy) | A normalised TriviaQA alias occurs as a whole word sequence in the generated reasoning text |
| Logical | Verdict matches gold label | Predicted *entailment* if the solver's verdict is ENTAILED, otherwise *not entailment*; compared with the RuleTaker label (`is_correct` field recorded by the pilot script) |

The factual label needs explanation. The factual pilot was run before the pipeline returned a separate final answer, so the result file stores the generated reasoning steps and the pipeline's claim-level output but no single answer string. Correctness was therefore approximated by checking whether any accepted alias, after lower-casing, removing articles and punctuation, and collapsing whitespace (the standard TriviaQA normalisation), appears in the generated reasoning. This proxy is lenient: reasoning that mentions the right entity while concluding something else would count as correct. Results based on it are labelled accordingly.

There are no step-level correctness labels in any pilot: GSM8K reference solutions do not align step-by-step with the model's solutions, and TriviaQA and RuleTaker label only the answer. All calibration metrics in Chapter 14 are therefore computed at the answer level, and error localisation cannot be evaluated (@sec:setup-not-measured).

## Metrics {#sec:setup-metrics}

For each pipeline, the analysis script `report/scripts/compute_metrics.py` computes the following from the answer confidence $c$ and correctness label $y \in \{0, 1\}$ of every completed question, using the project's own metric implementations (Chapter 10):

- **Accuracy** and the number of questions;
- **mean confidence** overall, for correct answers and for wrong answers;
- **ECE and MCE** over 10 equal-width bins, the **Brier score**, **NLL** and **AUROC** (definitions in Chapter 2); AUROC is reported as undefined when only one class is present;
- the **reliability bins** (count, mean confidence and accuracy per non-empty bin);
- **per-signal statistics** (mean, spread) and the **point-biserial correlation** of each signal with correctness (the Pearson correlation between a continuous score and a 0/1 label);
- pipeline-specific counts: step types and semantic entropy (arithmetic); claims per answer, claim verdicts, source statuses, reliability tiers and text origins (factual); the verdict confusion matrix, proof lengths and inconsistency detections (logical).

For the logical pilot the script additionally re-runs premise extraction, rule extraction, the rule engine and the Z3 solver *offline* on every completed question with the current code, to measure the effect of the rule-parser fix described in Chapter 9. This re-check needs no model calls, because the verdict is decided by the solver alone; it changes the verdict and the proof, but not the model-based signals, so it is reported as verdict accuracy only. Similarly, the 160 sources retrieved in the factual pilot are re-scored with the current reliability policy to show its effect on source status.

## Cost per Question by Design {#sec:setup-cost}

The pilot scripts did not log run time or count model calls. @tab:calls gives the number of model calls *by design*, derived from the code, and the expected count implied by the mean chain length observed in each pilot. These are design counts, not measurements; a sampling call returns K continuations in one request but is billed for all K outputs.

Table: Model calls per question by design (excluding the gateway classifier, which adds one call when questions go through `/api/ask`). {#tab:calls}

| Pipeline | Calls per question | Mean chain length in pilot | Implied calls (pilot mean) |
|---|---|---|---|
| Arithmetic | 1 generation + 2 per step (sampling with n = K, verification) | 6.4 steps (n = 5) | 13.8 |
| Factual | 1 generation + 2 per claim (web search, assessment) | 2.95 claims (n = 40) | 6.9, plus up to 2 page fetches per claim |
| Logical | 1 generation + 2 per proof step (sampling with n = K, verification) | 1.14 steps (n = 44) | 3.3 |

## Hardware and Environment {#sec:setup-hardware}

All runs used a Windows 11 workstation without a GPU; all model inference is hosted. The software versions are listed in Chapter 12. Network access to the OpenAI API and to the public web (for factual page fetches) was required during the runs; the analysis in Chapter 14 requires neither.

## Reproducibility {#sec:setup-repro}

Every number in Chapter 14 is computed by `compute_metrics.py` from files in the repository: the three pilot result files, the run store and the test suite. The script writes `report/results/metrics.json` and per-question CSV tables, and `report/results/RESULTS_SOURCES.md` maps every reported number to its file and field. Charts are produced from those outputs by `make_charts.py`. Appendix A gives the exact commands.

Two parts of the pipeline cannot be reproduced exactly by re-running the pilots. The hosted models may change behind the same model name, and sampling at temperature 0.8 is random by design; and web search results and page contents change over time. The *analysis* is exactly reproducible from the stored outputs; the *outputs* are reproducible only up to these sources of variation (Chapter 16).

## Not Measured {#sec:setup-not-measured}

Three quantities that the project set out to measure could not be measured with the available data, and are reported as such rather than estimated:

1. **Error-localisation accuracy (Top-1, Top-2).** No pilot contains a known error step: all five GSM8K answers were correct, TriviaQA and RuleTaker label only the answer, and the error-injection experiment (Chapter 7) has not yet been run against the pipeline.
2. **Run time and model calls per question.** Not logged by the pilot scripts; @tab:calls gives design counts instead.
3. **Gateway classification accuracy.** The pilots bypass the gateway.
