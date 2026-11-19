# Results and Analysis

This chapter reports what the three pilots and the stored runs show. Every number is computed by `report/scripts/compute_metrics.py` from files in the repository and traced in `report/results/RESULTS_SOURCES.md`; the sample size is given with each number. The pilots are small (5, 40 and 44 questions), so the results are indicative: differences of a few percentage points are within noise, and conclusions are drawn only where the effect is large or structural. Sections @sec:res-arith to @sec:res-logical take each pipeline in turn, @sec:res-runs covers the runs stored by the application, @sec:res-cross compares the pipelines, and @sec:res-rq answers the research questions posed in Chapter 5.

## Summary {#sec:res-summary}

@tab:res-summary gathers the headline numbers. Three findings dominate the rest of the chapter.

1. **Every pipeline runs end to end on its benchmark** and produces a step-level confidence profile with the signals behind it; this part of the design works as intended.
2. **Answer confidence does not yet discriminate correct from wrong answers.** AUROC is 0.516 for factual (n = 40) and 0.430 for logical (n = 44), close to or below the 0.5 of a random score; for arithmetic it is undefined because all five answers were correct.
3. **The causes are specific and fixable**, and most were found through this analysis: a rule-parser defect in the logical pipeline (fixed, accuracy 29 → 33 of 44), instruction-like "claims" in the factual pilot (70% of all claims), a confidence that scores the queried statement rather than the answer in the logical pipeline, and a verifier that rarely doubts a step in the arithmetic pipeline.

Table: Headline results (answer level). Confidence values are means; metrics use the correctness labels of Chapter 13. {#tab:res-summary}

| Metric | Arithmetic (GSM8K) | Factual (TriviaQA) | Logical (RuleTaker) |
|---|---|---|---|
| Questions completed / selected | 5 / 5 | 40 / 100 | 44 / 100 |
| Accuracy | 5/5 (100%) | 28/40 (70%, alias proxy) | 29/44 (66%); 33/44 (75%) after parser fix |
| Mean confidence | 0.619 | 0.676 | 0.471 |
| Mean confidence, correct / wrong | 0.619 / — | 0.668 / 0.694 | 0.477 / 0.459 |
| ECE (10 bins) | 0.381 | 0.238 | 0.282 |
| MCE (10 bins) | 0.401 | 0.602 | 0.510 |
| Brier score | 0.146 | 0.261 | 0.284 |
| NLL | 0.480 | 0.724 | 0.761 |
| AUROC | undefined (one class) | 0.516 | 0.430 |
| Steps or claims per answer | 6.4 steps | 2.95 claims | 1.14 proof steps |
| Calibration status | weighted proxy | fixed sigmoid | fixed sigmoid |

@fig:res-reliability shows the reliability diagrams, @fig:res-hist the distribution of answer confidence for correct and wrong answers, and @fig:res-roc the ROC curves.

![Reliability diagrams of answer confidence. Bars are the observed accuracy in each non-empty confidence bin; dots are the mean confidence in the bin; the dashed line is perfect calibration.](reliability_diagrams.png){#fig:res-reliability}

![Answer confidence for correct (green) and wrong (red) answers.](confidence_hist_correct_wrong.png){#fig:res-hist}

![ROC curves of answer confidence against correctness. Both curves lie close to the chance diagonal.](roc_curves.png){#fig:res-roc}

## Arithmetic Pipeline (GSM8K, n = 5) {#sec:res-arith}

### Answers and calibration

All five GSM8K answers matched the reference number (18, 3, 70,000, 540 and 20). The mean answer confidence was 0.619, between 0.599 and 0.624 for every question. Because every answer was correct, the pipeline was *under-confident*: the ECE of 0.381 is simply the gap between 100% accuracy and a mean confidence of 0.62, and AUROC is undefined. With five questions and no errors, these numbers say nothing about discrimination; they show only that the minimum-step aggregation produces conservative answer confidences.

### Steps and signals

The five solutions had 32 steps in total (3 to 13 per question, mean 6.4). The verifier classified 22 of them as `arithmetic`, 4 as `factual_recall`, 3 as `setup`, 2 as `logical_inference` and 1 as `conclusion` (@fig:res-arith-steps, left). @tab:res-arith-signals summarises the step-level signals.

Table: Step-level signals in the GSM8K pilot (32 steps). {#tab:res-arith-signals}

| Signal | Mean | Std. dev. | Min | Median | Max |
|---|---|---|---|---|---|
| Verification ($V$, `p_true`) | 0.984 | 0.036 | 0.90 | 1.00 | 1.00 |
| Consistency ($A$) | 0.525 | 0.303 | 0.20 | 0.40 | 1.00 |
| Sample agreement (exact match) | 0.356 | 0.211 | 0.20 | 0.30 | 1.00 |
| Semantic entropy ($H$, 30 steps) | 0.627 | 0.366 | 0.00 | 0.742 | 1.00 |
| Token probability ($T$) | 0.827 | 0.072 | 0.683 | 0.822 | 1.00 |
| Token entropy | 0.144 | 0.058 | 0.001 | 0.142 | 0.255 |
| Fused step confidence | 0.784 | 0.123 | 0.599 | 0.765 | 1.00 |

Three observations follow.

- **The verifier almost never doubts a step.** `p_true` averaged 0.984 and never fell below 0.90. On correct solutions this is right, but it means the verification signal contributed almost no variation; the fused confidence correlated 0.943 with consistency alone.
- **Semantic grouping matters.** Consistency (semantic clusters) averaged 0.525 while exact-match agreement averaged 0.356: continuations that the verifier judged equivalent were often worded differently. Exact-match agreement would therefore have made correct steps look much less stable.
- **Consistency and semantic entropy are nearly redundant.** Their correlation was −0.991 (@fig:res-arith-steps, right), as expected since both are functions of the same cluster sizes; token probability and token entropy were similarly related (−0.923). For a learned calibrator only one of each pair adds information.

![GSM8K pilot: step types assigned by the verifier (left) and consistency against semantic entropy for each step (right).](arithmetic_steps.png){#fig:res-arith-steps}

Two steps (6%) fell back to exact-match consistency because the verifier did not return a valid cluster list. By step type, mean fused confidence was 0.846 for factual-recall steps (n = 4), 0.783 for arithmetic steps (n = 22) and 0.702 for setup steps (n = 3).

### What the profile shows

@fig:res-chains (left) shows the confidence profile of one solution. Even though every step was correct, the profile is not flat: the lowest step (confidence 0.60) is the first one, where the five sampled continuations differed in how they started the solution. Across the five questions the flagged step was at a mean relative position of 0.58 in the chain (0 = first, 1 = last). With no wrong answers, these flags are by definition false alarms: they mark where the model was least certain how to *continue*, which is not the same as where it was wrong. Section @sec:res-localisation returns to this.

![Example step-confidence profiles from each pipeline; the lowest or flagged step is shown in red.](example_step_chains.png){#fig:res-chains}

## Factual Pipeline (TriviaQA, n = 40) {#sec:res-factual}

### Answers and calibration

By the alias-in-reasoning proxy, 28 of 40 answers (70%) were correct. Mean answer confidence was 0.676, and it was *slightly higher for wrong answers* (0.694) than for correct ones (0.668). AUROC was 0.516 (n = 40), ECE 0.238 and Brier score 0.261. The reliability diagram (@fig:res-reliability, centre) shows the shape of the miscalibration: the largest bin, mean confidence 0.85 with 17 questions, had accuracy 0.71 (over-confident), and the bin at 0.76 (5 questions) had accuracy 0.40; the lowest bin, mean confidence 0.27 with 4 questions, had accuracy 0.75 (under-confident). The confidence ceiling of 0.900 imposed by the fixed sigmoid is visible: no answer exceeded it.

### Claims, verdicts and instruction-like steps

The 40 answers were decomposed into 118 claims (2 to 6 per answer, mean 2.95). Of the 118 claims, 70 (59%) were judged SUPPORT, 3 (3%) CONTRADICT and 45 (38%) UNKNOWN (@fig:res-verdicts).

The most important finding for this pipeline is the *kind* of claim being verified. In 83 of the 118 claims (70%), present in all 40 answers, the "claim" was an instruction rather than an assertion: "Identify the creator of The Chipmunks", "Recall the year …". These came from generated reasoning steps that described *how* to answer instead of stating facts. An instruction cannot be true or false, yet 47 of the 83 were judged SUPPORT (the evidence was about the right topic), 33 UNKNOWN and 3 CONTRADICT. Because most of each answer's confidence was therefore computed from non-claims, it is not surprising that it carried little information about whether the answer was right. This finding led to the change in the factual generation prompt described in Chapter 8, which now forbids instruction-like steps and appends the model's final answer as an explicitly scored step; the pilot predates that change.

![Verification verdicts in each pipeline: claims in the factual pilot and the stored runs, and answers in the logical pilot.](claim_verdicts.png){#fig:res-verdicts}

### Signals

At claim level, self-verification averaged 0.592, verdict consistency 0.705 and the evidence score 0.605 (n = 118). None of them was correlated with answer correctness: the point-biserial correlations were −0.028 (self-verification), −0.166 (consistency) and −0.032 (evidence). Each signal is bimodal, with medians of 0.8, 1.0 and 0.78 and many zeros, reflecting claims with no usable evidence.

### Sources

The 118 claims retained 160 evidence sources from 73 distinct domains, 1.36 per claim on average; some claims retained none. 145 sources (91%) carried text fetched from the page itself and 15 (9%) carried citation-linked excerpts from the search model, so the page-fetch fallback was the normal path. The most frequent domains were `encyclopedia.com` (12 sources), `legalclarity.org` (9), and `newikis.com`, `villagepreservation.org` and `music.apple.com` (6 each).

At run time, 16 sources (10%) were marked KEEP and 144 (90%) DOWN_WEIGHT; none was rejected. Mean reliability was 0.563, and the median was the default 0.52. Re-scoring the same sources with the current 22-tier policy (@fig:res-sources) changes this to 35 KEEP and 125 DOWN_WEIGHT, raising mean reliability to 0.617. The re-scored sources fall into the tiers *general* (84), *general organisation* (40), *reference* (15), *government* (13), *reputable news* (3), *academic* (2), *intergovernmental* (2) and *news* (1). The policy change does not alter the pilot's confidences, which were computed at run time, but it shows that more than half of the evidence comes from sites outside any curated tier, which is a reminder that open web search for trivia questions mostly returns low-reputation sources.

![Retrieved sources in the factual pilot: status recorded at run time compared with the current policy (left), and their tiers under the current policy (right).](retrieved_sources.png){#fig:res-sources}

@fig:res-factual-dist shows the distribution of claims per answer and of source reliability before and after re-scoring.

![Factual pilot: claims per answer (left) and the reliability of retrieved sources, recorded and re-scored (right).](factual_distributions.png){#fig:res-factual-dist}

### Error localisation

The factual pipeline flagged step 1 in 17 answers, step 2 in 14, step 3 in 8 and step 4 in 1 (n = 40). With no step-level labels, these flags cannot be scored.

## Logical Pipeline (RuleTaker, n = 44) {#sec:res-logical}

### Verdicts

In the pilot run, 29 of 44 answers (66%) agreed with the RuleTaker label. The confusion matrix (@fig:res-confusion, left) is revealing: **all 8 ENTAILED and all 8 CONTRADICTED verdicts were correct; every one of the 15 errors was an UNKNOWN verdict on a question whose gold label is *entailment*.** The solver never gave a wrong definite answer. It failed only by not proving things it should have proved.

![RuleTaker verdict confusion matrices: as recorded in the pilot (left) and after the rule-parser fix, re-checked offline (right).](logical_confusion.png){#fig:res-confusion}

### Case study: the rule-parser defect

The pattern above prompted an investigation into why so many provable queries were UNKNOWN, and why 38 of 44 proofs had a single step. As described in Chapter 9, the rule extractor did not treat *something* and *it* as variables, kept the head noun of "All furry things are round", dropped bare generic plurals such as "Red things are big", and lost the subject of the second clause of a conjunction. On the RuleTaker knowledge bases, every rule was therefore either unusable or missing, the forward-chaining engine derived nothing, and the solver could prove only facts stated verbatim.

After the parser was fixed, the same 44 questions were re-checked offline with the solver (@fig:res-before-after). Accuracy rose from 29 to 33 (75%): four entailment questions moved from UNKNOWN to ENTAILED, and three not-entailment questions moved from UNKNOWN to CONTRADICTED, with no new errors (@fig:res-confusion, right). Proofs after the fix had one step in 40 questions and two steps in 4, consistent with the *depth-1* configuration of the completed questions.

![RuleTaker verdict accuracy before and after the rule-parser fix (n = 44).](logical_before_after.png){#fig:res-before-after}

### The remaining misses: open versus closed world

All 11 remaining misses are entailment questions answered UNKNOWN, and all 11 require the closed-world assumption under which RuleTaker is labelled (Chapter 9). Nine are negated queries ("Is Bob not quiet?") whose negation is true only because the positive fact cannot be derived; the other two ("Is Anne green?", "Is Dave nice?") depend on rules with negated conditions, such as "If something is not young then it is green", which fire under the closed-world assumption ("Anne is not young" because youth is unprovable) but not under open-world semantics. These are disagreements of semantics, not parser or solver errors. A closed-world option would answer them as the benchmark expects; whether it should be the default is discussed in Chapter 16.

### Confidence

Answer confidence was barely different for correct (0.477) and wrong (0.459) answers, and AUROC was 0.430, below chance (n = 44). @fig:res-logical-conf explains why. Confidence is grouped by *verdict*, not by correctness: ENTAILED answers averaged 0.738, while CONTRADICTED answers averaged 0.399 and UNKNOWN answers 0.415. As explained in Chapter 9, the confidence scores the probability that the *queried statement* is true, and its logical-validity component is 1 only when the statement is entailed. A correct "No" answer is therefore given low confidence by construction. All 8 CONTRADICTED answers were correct and all received low confidence, which by itself pushes AUROC below 0.5.

![Logical pilot: answer confidence of every question, grouped by the solver's verdict and coloured by correctness.](logical_conf_by_verdict.png){#fig:res-logical-conf}

Within the 28 UNKNOWN answers, the only group that contains errors, confidence was *higher* for the 15 wrong answers (0.459) than for the 13 correct ones (0.365), giving AUROC 0.215. In other words, the model-based signals tended to believe the queried statement in exactly the cases where it was in fact entailed but the defective parser had prevented the solver from proving it. The model's self-verification thus carried real information that the symbolic side had lost. This supports the multi-signal design: when one signal fails, another can disagree, and the disagreement is informative.

The individual signals of the essential claim (n = 44) were low overall: self-verification averaged 0.323 (median 0.1), consistency 0.332 (median 0.2), and logical validity 0.182 (8 of 44 entailed). Semantic entropy averaged 0.847 (median 1.0, n = 42): in most questions, all five sampled next steps were judged to mean different things. This is the weakness of next-step sampling noted in Chapter 9: in a knowledge base with many facts, there are many valid next inferences, so samples diverge even when the reasoning is sound. Logical validity had the strongest correlation with correctness (0.339), self-verification a negative one (−0.207) and consistency a weak one (0.137). No inconsistent knowledge base occurred among the 44 questions.

## Stored Application Runs {#sec:res-runs}

The application stored 29 runs between 15:28 and 17:24 UTC on 19 November 2026: 17 factual, 8 logical and 4 arithmetic (@fig:res-time); 23 contain the full pipeline output. Mean answer confidence was 0.824 for factual runs, 0.581 for logical runs and 0.658 for arithmetic runs. These runs have no correctness labels; they were questions typed during development and demonstration, several of them repeated. Four observations are nonetheless useful:

- **Repeated questions get similar but not identical confidences.** "What is the capital of India?" was asked four times as a factual question and received 0.89 or 0.90 each time. "What is the difference between LSTM and GRU?" was asked four times and received 0.70, 0.71, 0.85 and 0.89, reflecting different decompositions and evidence on each run (web results and sampling vary).
- **Unverifiable answers with a confidence.** Five factual runs ended with "The answer could not be verified from the available evidence." while still reporting confidences of 0.27, 0.70, 0.71, 0.83 and 0.83. The confidence had been computed over supporting claims that were verified, while the final answer itself was not. The current pipeline scores the final-answer step explicitly to close this gap (Chapter 8).
- **Correct logical answers with modest confidence.** "Is Anne red?", answered from premise p5 by the solver (ENTAILED, validity 1.0), received 0.601 on each of three runs, because self-verification and consistency were both 0.2, the next-step sampling effect described above. The single-step proof was flagged as the predicted error step, because with one step the arg-min rule has no alternative. A fourth run of the same question returned UNKNOWN (0.554) because the pasted text ended with a stray quotation mark after the question mark, so no sentence ended in "?" and no target was extracted; this is a robustness gap in premise extraction.
- **A false alarm on a valid proof.** In the three-step proof for "Is Niko a certified operator?" (Chapter 6), every step was entailed, yet step 2 was flagged (0.660) because only one of five samples agreed with it.

![Answer confidence of the stored application runs over time, by pipeline.](confidence_over_time.png){#fig:res-time}

## Cross-Pipeline Analysis {#sec:res-cross}

### Signal correlation

Across all 200 scored steps and claims of the three pilots, the signals were strongly correlated with each other (@fig:res-heatmap): self-verification and domain evidence correlated at 0.83, and each correlated at 0.90 with the final step confidence; consistency was more independent (0.47 with self-verification, 0.54 with domain evidence). The high correlation between self-verification and evidence is mostly a factual-pipeline effect, because the assessment call sees the same evidence that produces the evidence score, so the two are not independent views. Consistency is the signal that adds the most independent information, which argues for keeping a resampling-based signal even where external evidence is available.

![Correlation between the step-level signals across all three pilots (200 steps and claims).](signal_correlation_heatmap.png){#fig:res-heatmap}

### Confidence along the chain

@fig:res-position plots mean step confidence by position in the chain. In the arithmetic pilot, confidence *rose* along the chain, from 0.70 at step 1 to 0.96 at step 6 (5 to 3 steps per position): later steps, which apply operations already set up, were reproduced more consistently than the opening steps, where the model must choose how to begin. In the factual pilot, confidence was flat (0.67 to 0.75 over steps 1–4). In the logical pilot, two-step proofs had lower confidence at step 2 (0.39, n = 6) than at step 1 (0.53, n = 44). There is no evidence in these data of confidence systematically decaying along a chain; the proposal's hypothesis that uncertainty accumulates in later steps is not supported for these short, mostly correct chains.

![Mean step confidence by position in the chain; labels give the number of steps at each position.](confidence_by_position.png){#fig:res-position}

## Error Localisation {#sec:res-localisation}

Error-localisation accuracy (Top-1, Top-2) could not be measured, because no pilot contains a known error step (Chapter 13). What the data do show is the behaviour of the arg-min flag on correct reasoning: it flagged a step in every one of the 5 correct GSM8K solutions, in all 38 single-step logical proofs (necessarily), and in the valid three-step "Niko" proof. The arg-min rule always flags exactly one step, so on correct chains every flag is a false alarm. The confidence of a flagged step on a correct chain was typically around 0.6. A threshold below which a step is flagged, which can be fitted once step-level labels exist, would allow the system to report "no likely error". Running the error-injection experiment (Chapter 7) is the most important missing measurement.

## Testing Summary {#sec:res-tests}

All 105 automated tests passed in the final run (Chapter 15), covering every module, including regression tests for the rule-parser defect and for the source-reliability policy.

## Answers to the Research Questions {#sec:res-rq}

**RQ1: Can step-level confidence be produced for arithmetic, factual and logical reasoning within one framework, using verification signals suited to each type?**
Yes. All three pipelines ran end to end on public benchmarks (5, 40 and 44 questions) and on 29 interactive questions, and produced a confidence for every step or claim together with self-verification, consistency and domain-evidence signals, stored in a common format and rendered by a common interface. The type-specific evidence sources (token statistics, reliability-weighted web evidence, an SMT solver) were all exercised.

**RQ2: How well calibrated and discriminative is the answer confidence derived from step-level signals?**
Not yet adequately. Discrimination was at chance level for factual answers (AUROC 0.516, n = 40) and below chance for logical answers (0.430, n = 44); calibration error was 0.24 to 0.38 ECE. The analysis identified specific causes: instruction-like claims (70% of factual claims), a confidence that scores the queried statement instead of the answer for logical "No" and "cannot be determined" answers, a defective rule parser (fixed), and hand-set calibration. Monotone recalibration alone could not fix discrimination (Chapter 10); the causes have to be addressed in the signals and their definitions.

**RQ3: Which signals carry information about correctness?**
In the logical pilot, solver validity was the most informative signal (correlation 0.339); notably, the model's self-verification disagreed with the solver in exactly the cases where the parser had failed (AUROC 0.215 within UNKNOWN answers, in the informative direction). In the arithmetic pilot, the verifier's `p_true` was nearly constant and consistency carried almost all the variation. In the factual pilot, no signal was correlated with answer correctness, a result confounded by the instruction-like claims. Across pipelines, consistency was the least redundant signal.

**RQ4: Can the lowest-confidence step localise the erroneous step?**
Not measured. The required step-level labels do not exist in the pilot data; the error-injection experiment that provides them is implemented but not yet run. On correct chains, the arg-min rule produces a false alarm in every chain, which motivates a learned flagging threshold.
