# Literature Gaps

The survey in Chapter 3 shows a field with mature tools for *calibrating* a single prediction and for *estimating* the confidence of a whole answer, and separate tools for *verifying* individual steps or claims. This chapter states the gaps between them that motivate Calibra, numbered for reference, each tied to the surveyed works, together with how Calibra addresses it and how far it succeeds. It closes with the gaps that the surveyed papers identify but Calibra does not attempt to close. The analysis builds on the team's earlier gap study (`Gaps.docx`), which compared the project's design against the core calibration papers.

## Gaps Addressed {#sec:gaps-addressed}

**Gap 1: Confidence is estimated for whole answers, not for reasoning steps.** Post-hoc calibrators [@guo2017; @arad2025], self-evaluation [@kadavath2022], elicited confidence [@xiong2024], semantic uncertainty [@kuhn2023] and semantic-level calibration [@lamb2025] all treat the answer as one unit. For multi-step reasoning, a single score cannot say where the reasoning failed, and averaging over the answer dilutes the one uncertain step.
*How Calibra addresses it:* the unit of confidence is the step or atomic claim in every pipeline; answer confidence is derived from the step profile (Chapters 6–10). *Status:* achieved for all three reasoning types.

**Gap 2: No method localises the likely error in a reasoning chain using confidence.** Answer-level methods can only flag an answer as doubtful. Step-level process reward models score steps but are trained rankers rather than confidence estimators [@lightman2023], and SelfCheckGPT scores sentences against whole-response samples [@manakul2023].
*How Calibra addresses it:* the lowest-confidence step is reported as the predicted error location, and Top-1 and Top-2 localisation metrics are implemented with a controlled error-injection utility (Chapters 7 and 10). *Status:* implemented; not yet evaluated, because no labelled error steps exist in the pilots.

**Gap 3: Sampling is done over whole responses, so instability cannot be located.** Self-consistency [@wang2023], semantic entropy [@kuhn2023] and semantic calibration [@lamb2025] sample complete answers from the question, mixing the uncertainty of every step.
*How Calibra addresses it:* prefix-conditioned sampling generates K alternatives for one step at a time, holding the preceding steps fixed, and groups them by meaning (Chapter 7). *Status:* achieved; the pilots show it is informative for calculations but misleading for proofs with many valid next inferences (Chapter 14).

**Gap 4: Confidence relies on one kind of signal.** Each family of methods has a known blind spot: self-evaluation fails where knowledge is weakest [@kadavath2022], consistency misses consistent errors [@manakul2023], and internal signals require model access [@chen2024inside]. Combinations exist [@xiong2024] but use only model-internal signals.
*How Calibra addresses it:* every step is scored by self-verification, consistency and a domain-evidence signal that does not come from the model being evaluated, and the three are fused (Chapter 10). *Status:* achieved as a design; fusion weights are hand-set and the fused confidence did not yet discriminate in the pilots.

**Gap 5: Methods are not adapted to the type of reasoning.** Confidence methods are applied uniformly, although calculations, factual claims and deductions fail differently and have different natural checks. Claim verification against evidence [@min2023] and solver-based deduction [@pan2023logiclm] exist, but as separate systems without confidence estimation.
*How Calibra addresses it:* a gateway routes each question to a pipeline built around the right check (token statistics, reliability-weighted web evidence or Z3 entailment), and arithmetic fusion weights depend on the step type (Chapters 6–9). *Status:* achieved.

**Gap 6: Evaluation measures calibration but not localisation, and assumes the confidence target is well defined.** Standard evaluation reports ECE, Brier score and AUROC [@guo2017; @naeini2015]. It has no measure of *where* an error is, and recent work shows that calibration conclusions depend on what the confidence is compared against [@dogah2026].
*How Calibra addresses it:* standard metrics are complemented by Top-k localisation metrics; and the pilots show that the target matters at step level too, since the logical confidence measured the queried statement rather than the answer (Chapter 14). *Status:* metrics implemented; localisation not yet measured; the target mismatch has been identified, and fixing it is planned.

**Gap 7: Uncertainty propagation through a chain is not modelled.** An early error makes later steps wrong even if each is locally valid; answer-level methods cannot express this, and step-level rankers score steps largely independently.
*How Calibra addresses it:* only partially. Each step is sampled conditioned on its preceding steps, so later steps are scored in the context of earlier ones, and arithmetic answer confidence takes the minimum over steps. No explicit propagation model is implemented, and the pilots found no systematic decay of confidence along the chain (Chapter 14).

## Gaps Not Addressed {#sec:gaps-not-addressed}

Three limitations identified in the surveyed calibration papers lie outside Calibra's scope, and the report makes no claim to solve them:

- **Normalisation-aware multi-class calibration** [@arad2025]. Calibra calibrates binary step correctness, not class-probability vectors, and does not implement NA-FIR or SCIR. Its contribution is to change the *unit* being calibrated, not the calibration algorithm.
- **Calibration under soft, distributional labels** [@dogah2026]. Calibra's step labels are binary; questions with genuinely disputed answers would require soft targets.
- **Semantic-level temperature scaling** [@lamb2025]. Calibra uses a hosted model whose sampling temperature can be set but whose logits cannot be recalibrated by training a temperature head. Its fixed sigmoid could be refitted (Chapter 10), but semantic recalibration of the model itself is not attempted.

## Summary {#sec:gaps-summary}

The central gap is granularity: the literature calibrates and estimates confidence for whole outputs, while the information needed to locate a reasoning error lies in individual steps. Calibra's contribution is to take established confidence signals, change their unit of analysis from the response to the step, add verification suited to each reasoning type, fuse the signals, and use the resulting profile to localise errors. The design addresses Gaps 1, 3 and 5 fully; Gaps 2, 4 and 6 are addressed in design and implementation but await fitted calibration and labelled data to be validated; and Gap 7 is addressed only partially.
