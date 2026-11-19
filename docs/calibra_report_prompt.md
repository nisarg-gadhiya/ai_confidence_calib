# Prompt: Calibra Final-Year Project Report (Word → LaTeX, ~150 pages)

> Paste everything below this line into your coding agent (e.g. Claude Code) opened at the root of the `ai_confidence_calib` repository. Before you start, place these in the repo:
> - `docs/papers/` → all research PDFs (Semantic-Level Confidence Calibration; Temperature Scaling Is Not Enough; Normalization-Aware Isotonic Techniques (NA-FIR/SCIR); plus any others you used) and `Gaps.docx`
> - `docs/format_reference/caliper-final-report.pdf` → format reference only
> - `assets/vjti_logo.png` → the VJTI logo

---

You are writing the final B.Tech project report for our project **Calibra: Step-Level Confidence Calibration for LLM Reasoning**. The report must be about **150 pages** and is produced in two phases: **Phase 1** builds a Word document (plus Markdown sources, figures and result files) from the codebase and the research papers. **Phase 2** converts that Word document into a LaTeX project that compiles to a ~150-page PDF with every figure and table included.

## 0. Ground rules (read first, apply everywhere)

1. **Source of truth.** Everything about Calibra comes from this repository: the code, every `.md` file (README, abstract, docs, pipeline READMEs, experiment notes), `backend/data/calibration_runs.json`, experiment scripts and their output files, the tests, `Gaps.docx`, and the papers in `docs/papers/`. Read all of them before writing anything. Start by listing every `.md` file and every experiment/result file in the repo, and read each one.
2. **Never invent numbers.** Every score, count, percentage, latency or metric in the report must come from a file in the repo or from a script you run. If a metric has not been measured, either (a) compute it by running the existing scripts/pipelines (see §2.3), or (b) state plainly in the report that it is not yet measured and why. Do not write placeholder numbers that look real.
3. **The Caliper report is a format reference only.** `docs/format_reference/caliper-final-report.pdf` is another team's project on container security. Copy its *layout and structure* (front matter, chapter style, literature-survey template, headers, captions, appendices). Do **not** copy any of its content, terminology, figures, results, references, or acknowledgements text. Nothing about containers, seccomp, Kubernetes, CALIPER, etc. may appear in our report. After writing, search the whole document for "CALIPER", "container", "seccomp", "Kubernetes", "Suratkar" and remove any hit.
4. **References must be real.** Only cite papers you can confirm exist (title, authors, venue, year). Use the uploaded papers plus well-known works in this area. If you cannot verify a reference, leave it out.
5. **Length comes from content, not padding.** Reach ~150 pages with substantive material: chapters, figures, tables, analysis and appendices. Do not inflate font size, line spacing or margins beyond the spec in §3.1, and do not repeat text.

## 1. Fixed front-matter details

- **Title:** Calibra: Step-Level Confidence Calibration for LLM Reasoning
- **Document type line:** "Final Report on"
- **Degree line:** Submitted in partial fulfillment of the requirements for the degree of Bachelor of Technology in Computer Engineering
- **Students (name and roll number, in this order):**
  - Aarya Pandey (231071003)
  - Khushbu Chaudhari (231081018)
  - Diksha Dhanmane (231081020)
  - Nisarg Gadhiya (231080022)
- **Under the Guidance of:** Prof. Sopan Kolte
- **Department:** DEPARTMENT OF COMPUTER ENGINEERING AND INFORMATION TECHNOLOGY
- **Institute:** VEERMATA JIJABAI TECHNOLOGICAL INSTITUTE
  (An Autonomous Institute Affiliated to Mumbai University)
  (Central Technological Institute, Maharashtra State)
  Matunga, MUMBAI – 400019
- **Academic year:** A.Y. 2026–2027
- **Logo:** `assets/vjti_logo.png`, centred on the title page between the guide's name and the department name, about 3.5 cm wide (as in the reference report).
- **Head of Department:** leave the placeholder `[Head of Department]` for us to fill in.

## 2. Phase 1 — Word document, Markdown sources, figures and results

### 2.1 Study the material

1. Map the repository: `frontend/`, `backend/app/`, `gateway/`, `arithmetic/`, `factual/`, `logical/`, `backend/app/services/`, `backend/data/`, tests, experiment scripts, `.env.example`. For each module, note its purpose, main classes and functions, inputs and outputs, and how it connects to the others.
2. Read every paper in `docs/papers/` and `Gaps.docx`. For each paper, extract: authors, venue, year, problem, method, results, limitations, and how Calibra relates to it or improves on it.
3. Collect every existing result: `calibration_runs.json`, experiment output files (GSM8K pilot, TriviaQA run, RuleTaker run), test results, and any logs.

### 2.2 Write the chapters as Markdown first

Write one Markdown file per chapter in `report/md/` (`00_front_matter.md`, `01_synopsis.md`, …). These are the editable sources; the Word document is built from them. Follow the chapter plan below. The page budgets are targets for the final A4 layout and add up to ~150 pages.

| # | Chapter | Target pages | Must contain |
|---|---|---|---|
| — | Front matter: Title page, Statement of Candidate, Approval Sheet, Certificate, Acknowledgement, Contents, List of Figures, List of Tables, List of Abbreviations | 12 | Same pages and order as the reference report, with signature tables for all four students. Abbreviations list should cover LLM, ECE, MCE, NLL, AUROC, SMT, CoT, RAG, API, etc., plus a "Terms used throughout" block (ENTAILED / CONTRADICTED / UNKNOWN, SUPPORT / CONTRADICT, KEEP / DOWN_WEIGHT / REJECT, p_true, semantic entropy). |
| 1 | Synopsis | 4 | Abstract, Problem Statement, Motivation in Brief, Objectives, Summary of Contributions, Summary of Results (real numbers), Organisation of the Report |
| 2 | Background and Motivation | 10 | How LLMs reason and fail (hallucination, arithmetic slips, invalid deductions); what calibration means (reliability diagrams, ECE, MCE, Brier, NLL, AUROC, with formulas); token-level vs semantic-level vs step-level confidence; temperature scaling, Platt, isotonic; self-consistency and semantic entropy; LLM-as-judge; retrieval-augmented verification; SMT solvers and Z3; why one generic heuristic is not enough across reasoning types |
| 3 | Literature Survey | 28 | 15–20 papers, each in the reference report's template: **Publication Details** (authors, venue, DOI), **Introduction**, **Proposed Solution**, **Results**, **Gap / Limitation**, **Relevance** (to Calibra). Include all papers in `docs/papers/` (the two "Temperature Scaling Is Not Enough" PDFs are the same paper; survey it once) and well-known verified works such as: Guo et al. 2017 (calibration of modern neural networks), Kadavath et al. 2022, Kuhn et al. 2023 (semantic entropy), Wang et al. 2023 (self-consistency), Lightman et al. 2023 (Let's Verify Step by Step), Manakul et al. 2023 (SelfCheckGPT), Min et al. 2023 (FActScore), Xiong et al. 2024 (eliciting LLM confidence), Cobbe et al. 2021 (GSM8K), Joshi et al. 2017 (TriviaQA), Clark et al. 2020 (RuleTaker), de Moura & Bjørner 2008 (Z3), Chen & Guestrin 2016 (XGBoost), Naeini et al. 2015 (ECE). End with a comparison table of all surveyed works vs Calibra's features. |
| 4 | Literature Gaps | 4 | Numbered gaps, each tied to surveyed papers, using `Gaps.docx` as the starting point, and how Calibra addresses each |
| 5 | Proposed Solution | 7 | Objective, Rationale, Research Questions (RQ1–RQ4), Design Principles, Objectives and Outcomes, Success Criteria, Scope (in / out), Work Allocation among the four members, Schedule (Gantt chart) |
| 6 | System Architecture | 10 | Overview diagram, component table, request lifecycle (sequence diagram for `POST /api/ask`), gateway classifier and router, shared services, persistence format of `calibration_runs.json` (with an annotated example record), repository organisation tree, models used and why |
| 7 | Methodology I: Arithmetic Pipeline | 9 | Step generation, next-step sampling (5 samples, T = 0.8, log-probs), verifier `p_true`, semantic grouping, consistency and semantic entropy (with formulas), type-dependent fusion weights (calculation 0.35/0.40/0.25; logical/setup 0.50/0.30/0.20), the XGBoost step calibrator and its features, `type_adaptive_weighted_proxy` labelling, error-injection design |
| 8 | Methodology II: Factual Pipeline | 10 | Answer → steps → atomic claims, web retrieval with page fetch fallback, the 22-tier source-reliability policy (full table of tiers and scores), KEEP/DOWN_WEIGHT/REJECT thresholds, SUPPORT/CONTRADICT/UNKNOWN verification, evidence score formula, fusion (0.4/0.3/0.3), sigmoid σ(−1 + 3.2·f), geometric mean over essential claims and why |
| 9 | Methodology III: Logical Pipeline | 10 | Premise and rule extraction (variables for something/it/they, generic plurals, conjunctions), Z3 encoding with a worked example, ENTAILED/CONTRADICTED/UNKNOWN and inconsistency detection, open-world vs closed-world, forward-chaining proof builder, proof-path step selection, fusion with logical validity |
| 10 | Signal Fusion, Calibration and Error Localisation | 6 | Common fusion framework across pipelines, answer-level aggregation, lowest-confidence step as predicted error location, what is hand-tuned vs fitted (`fixed_sigmoid_not_empirically_calibrated`), calibration training script and its metrics |
| 11 | Frontend and Dashboard | 6 | Ask view (gauge with High/Moderate/Low bands, per-step chart, signal breakdown, reasoning chain, premises view, raw JSON), Analytics view (summary figures, charts, run history), themes, colour-blind-safe palette, mobile layout. Include real screenshots (see §2.4). |
| 12 | Technology Stack | 5 | Languages, frameworks, libraries with versions (from `requirements.txt` / `package.json`), APIs, configuration via `.env`, development environment, version control |
| 13 | Experimental Setup | 6 | Datasets (GSM8K test, TriviaQA rc.nocontext validation, RuleTaker test) with selection rules, sample sizes, models, sampling settings, hardware, cost and runtime per question, labelling of correctness, metrics and how each is computed, reproducibility |
| 14 | Results and Analysis | 18 | One section per pipeline plus a cross-pipeline section (see §2.3 for the required numbers and figures). Includes the parser-bug case study (29/44 → 33/44), the confidence-separation analysis (0.48 vs 0.46 in the logical pilot), the 11 closed-world misses, factual claim-verdict breakdown, source-reliability distribution, error-localisation results, and answers to each research question. |
| 15 | Testing and Validation | 5 | The 105 pytest tests grouped by module (table), stubbing strategy for LLM calls, what each group verifies, run time, sample test output |
| 16 | Discussion | 6 | What worked, what did not, Limitations, Threats to Validity (small pilot sizes, LLM-judge bias, label mismatch with closed-world RuleTaker, web-source drift), Ethical considerations, Lessons Learned |
| 17 | Conclusion and Future Work | 3 | Conclusion against each objective; future work from the repo's "Next Steps" |
| — | References | 5 | IEEE style, numbered in order of citation |
| — | Appendices | ~10 | A: Reproducing the results (exact commands). B: API reference (`/api/ask`, `/api/runs`, `/api/health` with request/response JSON). C: Prompts used for classifier, generator, verifier, claim splitter. D: Sample full run outputs for one question per pipeline. E: Source-reliability policy table in full. F: Project record (timeline, milestones, repo statistics). |

Writing style: formal academic English in the third person plural ("we"), explanations precise enough that an examiner who has not seen the code can follow each pipeline. Define every formula's symbols. Every figure and table is numbered, captioned, and referred to in the text.

### 2.3 Results and scores for all three pipelines

Write `report/scripts/compute_metrics.py` that reads `calibration_runs.json` and all experiment output files and produces `report/results/metrics.json` and CSV tables. For **each pipeline (arithmetic, factual, logical)** report, wherever correctness labels exist:

- Number of questions attempted / completed, answer accuracy
- Mean confidence overall, for correct answers and for wrong answers
- ECE (10 equal-width bins), MCE, Brier score, NLL, AUROC (confidence vs correctness)
- Error-localisation accuracy (does the flagged step match the injected or labelled error step?)
- Per-signal statistics (self-verification, consistency, domain evidence) and their correlation with correctness
- Pipeline-specific: arithmetic (step-type breakdown, semantic entropy distribution); factual (claims per answer, SUPPORT/CONTRADICT/UNKNOWN counts, sources kept/down-weighted/rejected, reliability distribution); logical (verdict confusion matrix vs gold labels, accuracy before and after the parser fix, inconsistency detections, proof lengths)
- Runtime and number of LLM calls per question, if logged

If the pilots are incomplete (factual 40/100, logical 44/100, GSM8K 5 questions), check whether an `LLM_API_KEY` is configured. If it is, ask me before running the remaining experiments, since they cost API credits; if I agree, finish them and use the new numbers. If not, report the existing numbers and state the sample size beside every metric. Where a metric cannot be computed (e.g. no correctness labels), say so in the report instead of omitting it silently.

Keep a `report/results/RESULTS_SOURCES.md` that lists, for every number in the report, the file and script it came from.

### 2.4 Figures and diagrams

Save every figure to `report/figures/` as 300-dpi PNG (and SVG where possible), generated by scripts in `report/scripts/` so they can be re-created. Use one consistent, colour-blind-safe palette and the same font throughout. Required at minimum (~35–45 figures in total):

- **Diagrams** (render Mermaid with `mermaid-cli` or use Graphviz): overall architecture; request sequence diagram; gateway routing flowchart; one detailed flowchart per pipeline; fusion and calibration flow; data model of a stored run; repository structure; deployment / run setup; Gantt chart; use-case diagram; a worked Z3 example diagram.
- **Charts from real data:** reliability diagram per pipeline; confidence histograms for correct vs wrong answers; ROC curves; per-step confidence along a chain (example per pipeline); signal-breakdown bars; signal correlation heatmap; fusion-weight comparison; the sigmoid mapping curve; source-reliability tier chart and distribution of retrieved sources; claim-verdict counts by pipeline; logical confusion matrix; logical accuracy before vs after parser fix; confidence by step position; confidence over time from stored runs; test count by module.
- **Screenshots:** run the frontend and backend locally, then take screenshots (Playwright) of the Ask view for one question of each type, the Analytics view, the run history, dark mode, and the mobile layout. If the app cannot be run, tell me and leave clearly marked placeholders.

### 2.5 Build the Word document

Build `report/Calibra_Final_Report.docx` from the Markdown files and figures (python-docx or docx-js, not a raw pandoc dump), matching the reference layout: A4, 12 pt serif body (Latin Modern Roman or Times New Roman if unavailable), justified, 1.15–1.25 line spacing, 2.5 cm margins; a centred title page with logo; front-matter pages numbered in lower-case Roman, chapters from Arabic 1; each chapter starting on a new page with "Chapter N" above the chapter title; a running header with the report title and page number; automatic Table of Contents, List of Figures and List of Tables; captions below figures and above tables; real Word tables (not images of tables).

### 2.6 Phase 1 check, then stop

Before finishing Phase 1:
- Convert the `.docx` to PDF (LibreOffice) and check the page count is 145–155. If it is short, add substance in Results, Methodology or Appendices; if long, tighten. Do not change font size or spacing to hit the target.
- Render a sample of pages to images and check them visually: title page and logo, a literature-survey page, a results page with figures, the contents pages.
- Check that every figure file is embedded, every figure and table is referenced in the text, every number appears in `RESULTS_SOURCES.md`, and the forbidden-words search from §0.3 is clean.

Then **stop** and send me a short summary: page count, number of figures and tables, any metrics that could not be computed, and any placeholders left. Wait for my go-ahead before Phase 2.

## 3. Phase 2 — Convert to LaTeX

### 3.1 Project layout and format

Create `report/latex/`:
```
main.tex
preamble.tex
frontmatter/  titlepage.tex, candidate.tex, approval.tex, certificate.tex, acknowledgement.tex, abbreviations.tex
chapters/     01_synopsis.tex ... 17_conclusion.tex
appendices/   A_reproducing.tex ... F_project_record.tex
figures/      (all PNG/PDF figures from Phase 1, plus vjti_logo.png)
references.bib
```
- `\documentclass[12pt,a4paper,oneside]{report}`, Latin Modern fonts (`lmodern`, `fontenc` T1), `geometry` with 2.5 cm margins, `setspace` at the same spacing as the Word version.
- `titlesec` for "Chapter N" headings in the reference style; `fancyhdr` running header (report title left, page number right); Roman page numbers for front matter, Arabic from Chapter 1.
- `graphicx`, `float`, `caption`, `subcaption`, `booktabs`, `longtable`, `tabularx`, `multirow`, `amsmath`, `amssymb`, `listings` (for code, JSON and commands), `hyperref` (coloured but print-friendly links), `cleveref`, `tikz`/`pgfgantt` if you redraw the Gantt chart, `biblatex` with IEEE style (or `IEEEtran.bst` with BibTeX).
- Title page reproduced exactly as in Phase 1, with `\includegraphics[width=3.5cm]{figures/vjti_logo.png}`.

### 3.2 Conversion rules

- Convert **all** content from the final Word document: every chapter, section, paragraph, equation, table, figure, caption, list and appendix. Nothing may be dropped or summarised.
- Equations become real LaTeX math (`equation` / `align`), numbered by chapter.
- Tables become `booktabs` tables (`longtable` for anything over a page). Figures use the same image files and captions, with `\label` and `\cref` references.
- Code, prompts, JSON and commands go in `listings` environments with line wrapping.
- All citations become `\cite{}` keys in `references.bib`, with the same references as the Word version.
- List of Figures, List of Tables and Table of Contents are generated by LaTeX.

### 3.3 Compile and verify

1. Compile with `latexmk -pdf main.tex` until there are no errors, no undefined references or citations, and no missing figures. Fix overfull hboxes that visibly run into the margin.
2. Check the page count with `pdfinfo`: it must be **145–155 pages**. If it is off, adjust content (not font size or margins), matching the Word version.
3. Run a completeness check: count figures, tables, chapters, sections and references in the Word document and in the PDF, and confirm they match. Confirm every file in `figures/` is used.
4. Render several pages to images (title page, contents, a survey page, a results page, an appendix) and check them visually.
5. Package `report/latex/` as `Calibra_Report_LaTeX.zip` (Overleaf-ready) alongside the compiled `main.pdf`.

### 3.4 Final deliverables

- `report/Calibra_Final_Report.docx`
- `report/md/*.md` (one per chapter)
- `report/figures/` and `report/scripts/` (all figure and metric scripts)
- `report/results/metrics.json`, CSV tables, `RESULTS_SOURCES.md`
- `report/latex/` (source), `report/latex/main.pdf`, `Calibra_Report_LaTeX.zip`

Finish with a short summary: final page count of both versions, figure/table/reference counts, and anything that still needs our input (Head of Department name, signatures, any unmeasured metrics).
