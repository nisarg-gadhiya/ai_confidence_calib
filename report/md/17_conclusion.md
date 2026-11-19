# Conclusion and Future Work

## Conclusion {#sec:conc-conclusion}

This project set out to move confidence estimation for large language models from the level of the whole answer to the level of the individual reasoning step, so that a system can say not only *how far* an answer should be trusted but *where* it is most likely to be wrong. We built Calibra, a working system that routes each question to an arithmetic, factual or logical pipeline, scores every step or atomic claim with a self-verification signal, a consistency signal and a domain-specific evidence signal, fuses them into a step confidence, aggregates the steps into an answer confidence, and flags the weakest step, all behind an interface that shows the evidence for every number. The conclusions against each objective of Chapter 5 are as follows.

**O1, step-level confidence for three reasoning types: achieved.** All three pipelines produce a confidence for every step or claim, with the signals behind it, on public benchmarks (GSM8K, TriviaQA, RuleTaker) and in interactive use.

**O2, multi-signal fusion with type-specific evidence: achieved as designed; effectiveness not yet established.** Token statistics from prefix-conditioned resampling, reliability-weighted web evidence and Z3 entailment were integrated with model self-verification and consistency. The solver was never wrong when it reached a definite verdict. The fused confidence, however, did not yet discriminate correct from wrong answers in the pilots (AUROC 0.516 factual, n = 40; 0.430 logical, n = 44), and the analysis traced this to specific causes rather than to the fusion idea itself.

**O3, answer confidence and error localisation: implemented; localisation not yet evaluated.** Answer confidence is derived from the step profile (minimum for arithmetic, geometric mean of essential claims otherwise) and the lowest-confidence step is flagged. Localisation accuracy could not be measured because no pilot contains a known error step; on correct chains, the arg-min flag always produces a false alarm.

**O4, a calibration and evaluation framework: achieved.** Standard calibration metrics, localisation metrics, a question-grouped XGBoost step calibrator and a controlled error-injection utility are implemented and tested, and the full analysis is reproducible from stored outputs. The calibrator has not yet been trained, for lack of step-level labels.

**O5, an explainable interface: achieved.** The Ask and Analytics views show the confidence profile, the flagged step, every signal, the evidence or proof, and the raw response, in light and dark themes and at phone width.

Beyond these objectives, the pilots produced findings of their own: a rule-parser defect whose fix raised RuleTaker verdict accuracy from 29 to 33 of 44; the observation that 70% of the claims verified in the factual pilot were instructions rather than assertions; the recognition that the logical confidence measured belief in the queried statement rather than in the answer; and evidence that the model's self-verification carried information that the symbolic solver had lost when the parser failed. These findings, and the decision to report them as they are, are part of the project's contribution.

In summary, Calibra demonstrates that step-level, type-aware, multi-signal confidence estimation can be engineered into a single transparent system, and it identifies concretely what must change before such confidence can be trusted.

## Future Work {#sec:conc-future}

The next steps follow directly from the results, in order of priority.

1. **Run the error-injection experiment.** Inject numeric errors into correct GSM8K solutions with the existing utility, score the corrupted chains, and report Top-1 and Top-2 localisation against uniform attribution. This measures the project's most distinctive claim.
2. **Attach confidence to the answer.** For logical questions, score the claim the answer expresses (the negated target for "No"; a dedicated "undetermined" claim for UNKNOWN). For factual questions, ensure the final answer is always a scored essential claim (already implemented, to be re-evaluated).
3. **Complete and repeat the pilots** with the current code: 100 questions per pipeline, then larger samples, with run time and model calls logged.
4. **Fit the calibration.** Collect step-level labels from error injection and the reference solutions; train the XGBoost calibrator for arithmetic; fit the sigmoid (Platt scaling) and, with enough data, the fusion weights for factual and logical claims by minimising NLL; report ECE, Brier, NLL and AUROC per pipeline with confidence intervals.
5. **Replace next-step sampling for proofs** with goal-conditioned or whole-answer sampling, so that consistency reflects agreement on the conclusion rather than on the choice of the next inference.
6. **Learn a flagging threshold**, so that the system can report "no likely error" on a chain whose steps are all confident, instead of always flagging one step.
7. **Offer a closed-world mode** for benchmarks and domains where unprovable statements should be treated as false, and report both semantics on RuleTaker.
8. **Strengthen factual relevance and verification**: semantic (embedding or NLI) relevance in place of lexical overlap, and an independent verifier model to reduce same-model judging bias.
9. **Add latent signals with a locally hosted model**: hidden-state probes and attention statistics per step, as in the original design, which the hosted API does not allow.
10. **Evaluate the gateway** on a labelled set of mixed questions, and extend the system with further reasoning types (for example code or tabular reasoning) through the same step-level interface.
