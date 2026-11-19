# Project Record

## Timeline

The proposal document (FYP-1) is dated 18 August 2026. @tab:commits lists the commits in the project repository; changes made after the last commit (the dashboard, the run-history endpoint, the revised source-reliability policy, the rule-parser fix and its tests, and this report) are in the working tree at the time of writing (28 modified and 16 new paths).

Table: Commit history. {#tab:commits}

| Commit | Date | Message |
|---|---|---|
| `e63babf` | 2026-09-27 | base project pushed |
| `2a37286` | 2026-10-03 | factual implemented |
| `5e78f1c` | 2026-10-03 | gateway is working |
| `1bb3808` | 2026-10-04 | logical questions model implemented |
| `e090a52` | 2026-11-19 | runned pilot tests |

## Milestones

- Problem definition, literature review and proposal (August 2026).
- Base project with the arithmetic pipeline (27 September 2026).
- Factual pipeline and gateway (3 October 2026).
- Logical pipeline with the Z3 solver (4 October 2026).
- Pilot experiments on GSM8K, TriviaQA and RuleTaker (19 November 2026).
- Dashboard, revised reliability policy, rule-parser fix, analysis and report (19 November 2026).

## Repository Statistics

Counted over files tracked by Git plus new files not yet committed, excluding the report itself and third-party dependencies; @tab:repo-stats gives the counts.

Table: Repository size by kind of file. {#tab:repo-stats}

| Kind | Files | Lines |
|---|---|---|
| Python (pipelines, backend, gateway) | 110 | 6,207 |
| Python (tests) | 8 | 1,840 |
| JavaScript / JSX (frontend) | 13 | 1,431 |
| CSS (frontend) | 1 | 1,079 |
| Markdown documentation | 12 | 491 |

## Deliverables

- Source code: frontend, backend, gateway, three pipelines, tests.
- Pilot result files for the three benchmarks and the run store.
- This report, its Markdown sources, figures, metric scripts and computed results under `report/`.
