# Synopsis

## Abstract {#sec:syn-abstract}

Large language models produce fluent answers but give no reliable signal of when they are wrong, and existing confidence methods score an answer only as a whole: they can suggest that an answer is doubtful, but not where its reasoning failed. This report presents **Calibra**, a system that estimates confidence for every step of a model's reasoning and uses the resulting profile both to derive an answer-level confidence and to flag the step most likely to contain an error. A gateway classifies each question as arithmetic, factual or logical and routes it to a pipeline built for that kind of reasoning. Every pipeline scores each step or atomic claim with three kinds of signal: the model's own verification of the step, the consistency of independent views of the step, and evidence from a source suited to the reasoning type. That evidence is token statistics of prefix-conditioned resamples for arithmetic, web evidence weighted by a 22-tier source-reliability policy for factual claims, and entailment checked by the Z3 SMT solver for deductions. The signals are fused into step confidences, aggregated into an answer confidence, and shown, with all their evidence, in a web interface with an analytics dashboard over every stored run. Pilot experiments on GSM8K (5 questions), TriviaQA (40) and RuleTaker (44) show that the system works end to end and that the solver never returned a wrong definite verdict. They also show that the answer confidence does not yet separate correct from wrong answers (AUROC 0.516 and 0.430). The analysis traces this to specific, fixable causes: a rule-parser defect whose correction raised RuleTaker accuracy from 29 to 33 of 44, instruction-like steps that made up 70% of verified factual claims, and a logical confidence that scored the queried statement instead of the answer. The report describes the design, the implementation and these findings, and sets out the work needed to fit and validate the calibration.

## Problem Statement {#sec:syn-problem}

Every established method for estimating an LLM's confidence, whether it asks the model, reads its token probabilities, samples it repeatedly, or groups its samples by meaning, treats the response as one indivisible unit. For multi-step reasoning this has two consequences. First, *error localisation is impossible*: a low score for a five-step derivation does not say whether step 1, 3 or 5 is wrong. Second, *the signal is diluted*: a model can be confident in four steps and uncertain in one, and a whole-response score averages the uncertain step away. In addition, the methods are generic, while reasoning failures are not: a wrong calculation, a hallucinated fact and an invalid deduction call for different checks. The problem addressed by this project is therefore to estimate confidence *for each reasoning step*, using checks suited to the *type* of reasoning, and to use the resulting step-level profile to localise likely errors as well as to score the answer.

## Motivation in Brief {#sec:syn-motivation}

LLMs are increasingly used to explain, calculate and argue, and people act on what they read. A confidence that points to the weak step would let a user check one step instead of the whole answer, let a downstream system re-generate or verify only that step, and make the model's uncertainty inspectable rather than a single opaque number. Because the three main kinds of reasoning error have natural external checks (recomputation, evidence and proof), a system that combines those checks with the model's own judgement has a principled basis for confidence that does not rely on the model alone.

## Objectives {#sec:syn-objectives}

1. Produce a confidence for every step of arithmetic, factual and logical answers within one framework.
2. Fuse self-verification, consistency and type-specific evidence into each step's confidence.
3. Derive an answer-level confidence and a predicted error step from the step-level profile.
4. Provide a framework for measuring calibration and localisation, including a trainable step calibrator and controlled error injection.
5. Make the confidence explainable through an interface that shows every signal and its evidence.

## Summary of Contributions {#sec:syn-contributions}

- **A step-level, type-aware confidence architecture**: a gateway and three pipelines that return a common step-level structure with every signal, a calibration-status label, and an answer confidence derived from the steps (Chapters 6–10).
- **Prefix-conditioned next-step sampling with semantic grouping** for arithmetic steps, combined with span-restricted token statistics and type-adaptive fusion weights (Chapter 7).
- **Reliability-weighted claim verification** for factual answers, with atomic claim extraction, web retrieval with a safe page-fetch fallback, and a documented 22-tier source-reliability policy (Chapter 8).
- **Solver-verified deduction with proof-path scoring** for logical questions, combining Z3 entailment and unsat cores with a forward-chaining proof builder, including the identification and correction of a rule-parser defect (Chapter 9).
- **An explainable interface and analytics dashboard** over every stored run (Chapter 11).
- **A reproducible evaluation** of all three pipelines on public benchmarks, with every number traced to a stored file, and an honest analysis of why the confidence does not yet discriminate (Chapters 13–14).

## Summary of Results {#sec:syn-results}

- **Arithmetic (GSM8K, n = 5):** 5/5 answers correct; mean answer confidence 0.619 (under-confident, ECE 0.381); AUROC undefined with one class. The verifier's `p_true` averaged 0.984, so consistency drove the confidence (correlation 0.943).
- **Factual (TriviaQA, n = 40 of 100):** 28/40 (70%) correct by an alias-in-reasoning proxy; mean confidence 0.668 for correct and 0.694 for wrong answers; AUROC 0.516, ECE 0.238. 83 of 118 verified claims (70%) were instructions rather than assertions. Re-scoring the 160 retrieved sources with the current policy raised the share kept at full weight from 10% to 22%.
- **Logical (RuleTaker, n = 44 of 100):** 29/44 (66%) correct as recorded and 33/44 (75%) after the rule-parser fix, with no new errors; all 16 ENTAILED and CONTRADICTED verdicts correct; all 11 remaining misses require the benchmark's closed-world assumption. AUROC 0.430, because correct "No" answers receive low confidence by construction.
- **System:** 29 interactive runs stored and visualised; 105 automated tests pass offline.
- **Not measured:** error-localisation accuracy (no labelled error steps yet), run time per question, and gateway accuracy.

## Organisation of the Report {#sec:syn-organisation}

Chapter 2 introduces the background: how LLMs fail, calibration and its metrics, and the families of confidence methods. Chapter 3 surveys the literature and Chapter 4 states the gaps it leaves. Chapter 5 presents the proposed solution, research questions and schedule. Chapter 6 describes the system architecture, and Chapters 7, 8 and 9 the arithmetic, factual and logical pipelines. Chapter 10 brings together fusion, calibration and error localisation. Chapter 11 presents the frontend and Chapter 12 the technology stack. Chapter 13 describes the experimental setup and Chapter 14 the results and their analysis. Chapter 15 covers testing, Chapter 16 discusses limitations, threats to validity and ethics, and Chapter 17 concludes, describes where the system can be applied in practice, and sets out its future scope. The appendices give the commands to reproduce the results, the API reference, the prompts, sample outputs, the full source-reliability policy and the project record.
