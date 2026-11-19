# Proposed Solution

Chapter 4 identified the gaps this project addresses. This chapter states the solution we proposed in response: its objective and rationale, the research questions it answers, the design principles it follows, its objectives and expected outcomes, how success is judged, its scope, how the work was divided, and the schedule.

## Objective {#sec:ps-objective}

To design, implement and evaluate a system that estimates the confidence of a large language model's answer *at the level of each reasoning step*, using verification signals suited to the kind of reasoning involved, and that uses the resulting confidence profile both to derive an answer-level confidence and to indicate the step most likely to contain an error.

## Rationale {#sec:ps-rationale}

Existing confidence methods treat an answer as one unit (Chapter 2): they say *whether* to trust an answer but not *where* it may have gone wrong, and averaging over a long answer dilutes the signal of the one step that is uncertain. A multi-step answer, however, is a chain of steps of different kinds, and each kind fails differently: a calculation fails by producing a wrong number, a factual statement by asserting something the world does not support, and a deduction by concluding something the premises do not entail. Each failure mode has a natural check: resampling the computation, consulting external sources, and proving the conclusion. A system that splits the answer into steps, applies the right check to each step, and combines the checks with the model's own judgement can both localise errors and, in principle, produce a better-founded answer confidence than any single signal.

The project began, as recorded in the proposal of August 2026, as an extension of a response-level calibration design ("CalibraLM") to step level. During implementation it became clear that the three reasoning types needed separate pipelines rather than one pipeline with type-dependent weights, because their evidence sources (token statistics, the web, a theorem prover) are structurally different. The gateway-and-pipelines architecture of Chapter 6 is the result.

## Research Questions {#sec:ps-rq}

- **RQ1.** Can step-level confidence be produced for arithmetic, factual and logical reasoning within one framework, using verification signals suited to each type?
- **RQ2.** How well calibrated and discriminative is the answer-level confidence derived from step-level signals?
- **RQ3.** Which signals (self-verification, consistency, domain evidence) carry information about correctness in each type of reasoning?
- **RQ4.** Can the lowest-confidence step localise the erroneous step in a reasoning chain?

Chapter 14 answers each question from the pilot data.

## Design Principles {#sec:ps-principles}

1. **The step is the unit.** Every score is computed for a step or atomic claim; answer confidence is derived from step scores, never estimated separately.
2. **Verify with the right tool.** Each reasoning type uses the external check that matches its failure mode, so that at least one signal does not come from the model under evaluation.
3. **Several weak signals beat one.** Self-verification, consistency and domain evidence each have a known blind spot (Chapter 10); they are combined so that one can cover another.
4. **Show the evidence.** Every signal behind every score is returned, stored and displayed.
5. **Never overstate calibration.** A score is called a calibrated probability only if it has been fitted to data; otherwise it carries a label saying how it was produced.
6. **Measure, then trust.** Every component is evaluated against labelled data before its output is relied upon, and the analysis is reproducible from stored outputs.

## Objectives and Outcomes {#sec:ps-objectives}

@tab:ps-objectives lists the five objectives of the project and the outcome expected from each.

Table: Objectives and expected outcomes. {#tab:ps-objectives}

| Objective | Expected outcome |
|---|---|
| O1. Produce a confidence for every step of arithmetic, factual and logical answers | Three pipelines returning a common step-level structure |
| O2. Fuse self-verification, consistency and type-specific evidence | Token statistics (arithmetic), reliability-weighted web evidence (factual), SMT entailment (logical), fused per step |
| O3. Derive answer confidence and localise errors from the step profile | Answer confidence and a predicted error step for every answer |
| O4. Provide a calibration and evaluation framework | Metrics (ECE, MCE, Brier, NLL, AUROC, Top-k localisation), a trainable step calibrator, controlled error injection |
| O5. Make the confidence explainable | An interface showing the profile, the flagged step, the signals and the evidence, plus analytics over stored runs |

## Success Criteria {#sec:ps-success}

The project defined success at two levels.

- **System level.** All three pipelines run end to end on a public benchmark; every response contains step-level confidences with their signals and a calibration-status label; every response is stored and can be re-rendered; the test suite passes without network access.
- **Evaluation level.** The answer confidence should discriminate correct from wrong answers better than chance (AUROC clearly above 0.5) on each benchmark; after fitting, calibration error should fall relative to the unfitted scores; and the lowest-confidence step should locate injected errors more often than uniform attribution ($1/n$ for an $n$-step chain).

Chapter 17 assesses the project against these criteria: the system-level criteria are met, while the evaluation-level criteria are not yet met (discrimination) or not yet measured (localisation, fitted calibration).

## Scope {#sec:ps-scope}

**In scope:**

- English questions of three types: arithmetic word problems, open-domain factual questions, and deduction from premises written in controlled English;
- hosted OpenAI models accessed through their API, with token log-probabilities as the only internal signal;
- step decomposition, per-step signals, fusion, answer aggregation and arg-min error localisation;
- a web interface and a JSON run store;
- pilot evaluation on GSM8K, TriviaQA and RuleTaker.

**Out of scope:**

- training or fine-tuning language models;
- hidden-state or attention-based signals, which require a locally hosted model;
- correcting the errors that are localised (the system flags, it does not repair);
- multilingual questions, images, code and tabular reasoning;
- free-form natural-language arguments beyond the supported controlled language;
- production deployment concerns such as authentication, multi-user storage and rate limiting.

## Work Allocation {#sec:ps-allocation}

@tab:ps-allocation lists the main work packages of the project. The allocation of work packages to team members is to be completed by the team.

Table: Work packages and allocation. {#tab:ps-allocation}

| Work package | Responsible member(s) |
|---|---|
| Literature review and problem definition | [to be filled by the team] |
| Arithmetic pipeline: generation, sampling, verification, fusion, calibrator | [to be filled by the team] |
| Factual pipeline: decomposition, retrieval, reliability policy, verification | [to be filled by the team] |
| Logical pipeline: extraction, Z3 solver, rule engine, scoring | [to be filled by the team] |
| Gateway, API, run store and shared services | [to be filled by the team] |
| Frontend: Ask and Analytics views | [to be filled by the team] |
| Experiments, analysis and testing | [to be filled by the team] |
| Report and presentation | [to be filled by the team] |

## Schedule {#sec:ps-schedule}

@fig:gantt shows the schedule. Completed phases are bounded by dated evidence: the proposal document is dated 18 August 2026, and the repository's commits mark the base project (27 September), the factual pipeline and gateway (3 October), the logical pipeline (4 October) and the pilot runs (19 November); the dashboard, the reliability policy revision and the parser fix were made on 19 November and are not yet committed. The start of the first phase is indicative. Phases after the report date are planned and indicative; they follow the priorities in Chapter 17.

![Project schedule for A.Y. 2026–2027. Solid bars are completed phases with dated evidence; hatched bars are planned.](gantt.png){#fig:gantt}
