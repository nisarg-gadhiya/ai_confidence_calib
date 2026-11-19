# Testing and Validation

Calibra is tested by an automated suite of 105 tests written with pytest. The tests run entirely offline, without network access or API credits, by replacing every model and web call with a stub. This chapter describes how the suite is organised, how stubbing is done, what each group of tests verifies, and how the suite caught or guards against specific defects described earlier in the report.

## Organisation {#sec:test-organisation}

The tests mirror the package structure (@tab:tests, @fig:tests). Parametrised tests count once per parameter set, so a single test function can contribute several tests: for example, one function checks ten domains against their expected reliability band.

Table: Test files and what they cover. {#tab:tests}

| File | Tests | Covers |
|---|---|---|
| `tests/arithmetic/test_research_evaluation.py` | 7 | Calibration metrics, AUROC edge cases, fusion weights, localisation metrics, error injection, XGBoost calibrator training |
| `tests/backend/test_import.py` | 1 | The backend application imports and initialises |
| `tests/backend/test_inference_pipeline.py` | 2 | Arithmetic inference: prefix-conditioned resampling and the exact-match fallback |
| `tests/backend/test_llm_service.py` | 12 | LLM client: prompts, structured output, token statistics, verification parsing, web-search citation handling, claim assessment validation |
| `tests/factual/test_factual_pipeline.py` | 37 | Claim extraction, retrieval, page fetching and its safety rules, source reliability, evidence aggregation, fusion, answer confidence, final-answer selection |
| `tests/gateway/test_gateway.py` | 16 | Classification schema, routing, the `/api/ask` endpoint, persistence to the run store, unmounted legacy endpoints |
| `tests/logical/test_logical_pipeline.py` | 30 | Premise and rule extraction, Z3 verdicts, inconsistency detection, proof construction, step selection, scoring and aggregation |
| **Total** | **105** | |

![Number of automated tests per module.](tests_by_module.png){#fig:tests}

## Stubbing Strategy {#sec:test-stubs}

Every external dependency is replaced at a single, well-defined seam:

- **Model calls.** The `LLMService` constructor accepts an injected client. Tests pass a small fake object that records the requests it receives and returns canned completions, including canned log-probability structures. This allows tests to assert both *what is sent* (for example, that the fixed prefix and the candidate samples appear in the verification prompt, or that the classification schema has `strict` mode and no additional properties) and *how responses are parsed*. Where a whole pipeline is under test, pytest's `monkeypatch` replaces the factory that creates the service (`get_factual_llm_service`, or `LLMService` inside the inference route) with a fake class.
- **Web search and page fetching.** `search_sources` and `_fetch_page_text` are replaced with functions that return fixed sources or page text, so retrieval logic is tested without the network.
- **HTTP endpoints.** Gateway tests use FastAPI's `TestClient` against the real application, with `route_question` patched to return a fixed pipeline result.
- **Persistence.** Tests that write calibration records point the run-store path at a temporary directory provided by pytest, so the real `calibration_runs.json` is never touched.
- **The solver.** Z3 is *not* stubbed: it is local, fast and deterministic, so the logical tests exercise the real solver on small knowledge bases.

The result is a suite that is fast (all 105 tests passed in 15.1 seconds as reported by pytest, 18.8 seconds of wall-clock time including interpreter start-up, on the development workstation) and deterministic, and that can run in any environment without credentials.

## What the Tests Verify {#sec:test-coverage}

### Calibration and evaluation

The research-evaluation tests check the metric implementations used throughout Chapter 14: that AUROC handles tied scores and returns no value when only one class is present; that the calibration report rejects probabilities outside [0, 1] and includes discrimination and reliability bins; that the localisation metrics score only cases whose final answer is wrong and whose error step is known; that error injection records the corrupted step and the original text; and that the XGBoost calibrator trains with a question-grouped hold-out, reports metrics, and can be saved and reloaded.

### Arithmetic inference and the LLM client

The inference tests check the property the arithmetic pipeline depends on: each step is resampled from *its own* fixed prefix (step 3's continuations see steps 1 and 2 only), and the step falls back to exact-match consistency when the verifier's cluster ids are malformed. The client tests check that token statistics exclude the JSON wrapper around `step_text`, that malformed cluster ids are discarded, that web search keeps only cited `http`/`https` sources, that claim assessments keep only verdicts for supplied sources, and that a missing API key is reported clearly.

### Factual pipeline

The factual tests cover each stage in isolation and the pipeline as a whole. Examples:

- claim extraction splits independent clauses but keeps coordinated lists together ("an input gate and a forget gate");
- the page fetcher refuses `localhost` and other non-public addresses, and the readable-text parser skips scripts and navigation;
- the reliability policy places each of ten representative domains in its expected band, ranks tiers in order, matches domains only on dot boundaries (so `notbbc.co.uk` does not inherit `bbc.co.uk`, and `entertainment.com` is not treated as official), and caps blog-typed sources;
- evidence aggregation weights support and contradiction by reliability and relevance;
- the answer confidence is the geometric mean over essential claims;
- the final answer is withheld when the final claim is not supported, and the model's unverified answer is preserved and marked as such.

### Gateway and persistence

The gateway tests check that the classification schema accepts exactly the three categories and rejects others, that each category is routed to its pipeline and that the pipeline result is returned unchanged (no wrapper object), that the arithmetic response through the gateway matches the direct inference function, that the legacy direct endpoints are no longer mounted, and that every answer is persisted with its step-level signals and, for factual answers, its source links.

### Logical pipeline

The logical tests check verdicts on small knowledge bases with known answers (syllogisms, contradictions, disjunctions, symbolic implications and propositional truth questions), that a disjunction does not entail either alternative, that contradictory premises are detected and reported with their unsat core, that unsupported syntax yields a conservative UNKNOWN rather than a misreading, and that a multi-step proof is scored step by step with only the final claim contributing to the answer confidence.

## Regression Tests from Defects Found {#sec:test-regressions}

Two defects found during the project, described in Chapters 8, 9 and 14, are now guarded by tests:

1. **Rule-parser defect (logical).** `test_ruletaker_style_rules_use_variables_and_generic_plurals` checks that a RuleTaker knowledge base yields all eight rules, that "something … it" binds one variable, that the second conjunct inherits its subject, and that "All furry things are round" and "Red things are big" are parsed. `test_ruletaker_style_rules_fire_in_solver` (five cases) checks the resulting verdicts, including one that requires a rule ("Is Anne round?" is ENTAILED) and one that requires the negation of a derived fact ("Is Anne not round?" is CONTRADICTED). `test_reasoning_steps_follow_only_the_target_proof` checks that steps are limited to the proof of the query, and `test_plain_it_fact_is_not_turned_into_a_variable` checks that the pronoun rule does not leak into facts.
2. **Source-reliability substring defect (factual).** `test_source_reliability_matches_domains_on_dot_boundaries` and the ten-case band test check that domains match only on dot boundaries and that each tier lands in its intended band.

## Sample Output {#sec:test-output}

The final run of the suite, made by the analysis script while producing this report, ended:

```
105 passed, 1 warning in 15.12s
```

The single warning is a deprecation notice from the HTTP test client library and does not affect the tests.

## Limitations of the Test Suite {#sec:test-limitations}

The suite verifies the *logic* of the system, not the *behaviour of the models*: because model calls are stubbed, it cannot detect a prompt that the real model misinterprets, and it does not measure accuracy or calibration; those are measured by the pilots (Chapter 14). There are no automated frontend tests; the interface was checked manually and through the screenshot script in light and dark themes and at phone width. Code-coverage measurement is not yet configured.
