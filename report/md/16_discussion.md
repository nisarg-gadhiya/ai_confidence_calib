# Discussion

This chapter steps back from the numbers. It discusses what worked and what did not, the limitations of the system and of the evaluation, the threats to the validity of the conclusions, the ethical considerations raised by a system that tells people how far to trust an AI, and the lessons the team draws from the project.

## What Worked {#sec:disc-worked}

**The architecture.** Separating *what kind of reasoning* a question needs (the gateway), *how that reasoning is verified* (three pipelines) and *how verification becomes confidence* (shared fusion and calibration) proved sound. The three pipelines use entirely different evidence, yet they return the same step-level structure, are stored in the same format and are rendered by the same interface. Adding the logical pipeline after the arithmetic and factual ones required no change to the API, the store or the frontend beyond presentation.

**Type-specific evidence.** Each pipeline's domain-evidence signal does something a generic heuristic could not. The Z3 solver never produced a wrong definite verdict in the logical pilot: all 16 ENTAILED and CONTRADICTED answers were correct, and every error was a failure to prove (Chapter 14). The factual pipeline verified claims against real pages rather than the model's memory, fetching page text for 91% of its sources. The arithmetic pipeline's token statistics are restricted to the exact span of each sampled step.

**Transparency as an engineering tool.** Storing every signal behind every score, and labelling every score with how it was produced, made the analysis in Chapter 14 possible from stored data alone, and it is what exposed the problems. The rule-parser defect was found because the stored proofs had one step where they should have had two; the instruction-like claims were found by reading the stored claims; the "Niko" false alarm was visible because the stored step showed a valid proof with low consistency. A system that reported only a final percentage would have hidden all three.

**Honest labelling.** No score in the system is presented as a calibrated probability unless it has been fitted, and the report follows the same rule. This kept the team from over-claiming results that the data do not support.

## What Did Not Work (Yet) {#sec:disc-not-worked}

**Discrimination.** The central quantitative goal, a confidence that ranks correct answers above wrong ones, is not met: AUROC was 0.516 (factual, n = 40) and 0.430 (logical, n = 44). The analysis attributes this to identifiable causes rather than to the idea of step-level confidence itself, but until those causes are removed and the pilots repeated, the claim that step-level multi-signal confidence *improves* calibration over response-level baselines remains untested.

**Next-step sampling for proofs.** Prefix-conditioned resampling assumes that a confident model will reproduce the same next step. That is reasonable for a calculation, where the next operation is largely determined, but not for a proof over a knowledge base with many facts, where many next inferences are equally valid. In the logical pilot, semantic entropy had a median of 1.0 (every sample different), dragging down the confidence of correct steps. For logical questions, sampling should be conditioned on the *goal* (what is to be proved) or replaced by sampling of the whole answer.

**What the confidence refers to.** In the logical pipeline, confidence measures belief that the *queried statement* is true, so correct "No" answers are given low confidence by construction. The same subtlety appeared in the factual pipeline, where confidence was computed over supporting claims while the final answer itself could be unverified. A confidence must be attached to the thing the user is asked to trust, which is the answer as stated.

**The verifier as a signal.** In the arithmetic pilot, the verifier's `p_true` averaged 0.984 with almost no variation; in the logical pilot it was low and noisy (median 0.1). A same-model verifier at temperature 0 appears to be either uncritical or erratic depending on the task, which limits its value as a fusion input until it is calibrated per pipeline.

**Localisation was not evaluated.** The error-injection experiment that would test the project's most distinctive claim, that the lowest-confidence step locates the error, has not been run.

## Limitations {#sec:disc-limitations}

**Scale of evaluation.** The pilots completed 5, 40 and 44 questions. Metrics such as ECE and AUROC have wide uncertainty at these sizes; a single question changes accuracy by 2 to 2.5 percentage points. The results identify problems reliably but cannot rank alternatives finely.

**Labels.** Correctness labels were answer-level only. The factual label is a lenient proxy (an alias appearing in the reasoning), and the logical labels follow closed-world semantics that the system deliberately does not adopt.

**Hand-set calibration.** All fusion weights, the sigmoid, the reliability tiers and every threshold were set by reasoning, not fitted (Chapter 10). The XGBoost calibrator is implemented but untrained.

**Hosted models.** The design originally included hidden-state signals; the hosted API does not expose them. The system also depends on one provider, with costs that scale with chain length (13.8 model calls for an average GSM8K question by design).

**Controlled logical language.** The logical parser handles RuleTaker-style controlled English and simple propositional forms. Natural arguments with *some*, *most*, nested clauses or implicit premises are reported as unsupported.

**Lexical relevance.** The factual pipeline's relevance filter is lexical and can discard relevant paraphrased evidence before the model sees it.

## Threats to Validity {#sec:disc-threats}

**Internal validity.** The pilots were run during development, and the code changed afterwards: the factual prompt, the final-answer scoring and the rule parser were all modified as a result of the pilot analysis. The offline re-check of the logical pilot isolates the effect of the parser fix on verdicts only; the model-based signals of the re-checked questions were not recomputed. The factual results describe a version of the pipeline that no longer exists in that form.

**Construct validity.** The factual correctness proxy can count a wrong answer as correct if the right entity is mentioned along the way, which would inflate accuracy and blur the relation between confidence and correctness. For logical questions, "correct" means agreement with closed-world labels, so part of what is measured as error is a difference in semantics.

**LLM-as-judge bias.** Self-verification, claim assessment and semantic grouping are all performed by the same model family that generated the answer. Such judges are known to favour fluent text and their own outputs [@zheng2023]; agreement between generator and judge is weaker evidence than it appears.

**External validity.** GSM8K, TriviaQA and RuleTaker are standard but narrow: grade-school arithmetic, trivia, and synthetic depth-1 rule bases. Behaviour on professional mathematics, contested or recent facts, or natural arguments may differ. The completed questions are the first of each selection, not a random sample, although selection did not depend on outcome.

**Temporal validity and drift.** Web search results and page content change, and hosted models change behind a fixed name. Re-running a pilot later can give different evidence, verdicts and confidences; the analysis of *stored* outputs is exactly reproducible, but the outputs themselves are not.

**Reproducibility of sampling.** Next-step sampling at temperature 0.8 is random by design, so consistency and entropy vary between runs even with the same model.

## Ethical Considerations {#sec:disc-ethics}

**Over-trust.** A confidence score can increase trust in an answer that does not deserve it. This risk is greatest exactly where Calibra is weakest at present: the pilots show confidences that do not separate right from wrong answers. The system mitigates the risk by showing the evidence behind every score, labelling uncalibrated scores as such, stating when a factual answer could not be verified, and using cautious *Moderate* and *Low* bands. It should not be deployed to non-expert users as a correctness guarantee until calibration has been fitted and validated.

**Source policy and bias.** The reliability policy encodes judgements about which publishers deserve trust. These judgements favour established, mostly English-language institutions, and a policy that rejects social media and forums by default will also exclude legitimate first-hand testimony and community knowledge. The tiers are documented in full (Appendix E) so that they can be inspected and challenged, and they should be reviewed by people with wider perspectives before any public deployment.

**Web access.** The factual pipeline fetches third-party pages. It identifies itself with a descriptive user agent, fetches at most two pages per claim with a short timeout and a size cap, caches results, refuses non-public addresses so that it cannot be used to probe internal networks, and stores only the short excerpts used as evidence.

**Data and privacy.** Every question is stored with its answer in a local file. Users may type personal or sensitive information into a question; in a deployment, the store would need a retention policy and users would need to be told that questions are kept and sent to a third-party model provider. The API key is read from a local configuration file, excluded from version control, and never logged or returned.

**Honest reporting.** The team chose to report negative and inconclusive results (below-chance AUROC, unmeasured localisation, incomplete pilots) as they are, rather than selecting favourable subsets. Several of the most useful findings of the project are among these negative results.

## Lessons Learned {#sec:disc-lessons}

1. **Inspect the intermediate outputs, not only the metrics.** The two most consequential defects (the rule parser and the instruction-like claims) produced plausible-looking final answers and were found only by reading the stored proofs and claims.
2. **Define what the confidence is about before computing it.** A confidence attached to the queried statement, or to supporting claims, is not a confidence in the answer. This must be fixed in the design, not in calibration.
3. **Sampling-based consistency needs a determined target.** It works when one next step is clearly right, and misleads when many are.
4. **Calibration cannot fix ranking.** Monotone recalibration changes the scale, not the order; if the order is wrong, the signals or their definitions must change.
5. **Plan the labelled data from the start.** Step-level labels (or controlled error injection) are needed for both calibration and localisation; without them, the project's two main claims cannot be measured.
6. **Small, structured pilots are cheap and revealing.** A few dozen questions per pipeline were enough to expose structural problems that would have wasted a full-scale run.
7. **Keep the system honest about itself.** Labelling every score with how it was produced cost little and prevented the team from mistaking a heuristic for a result.
