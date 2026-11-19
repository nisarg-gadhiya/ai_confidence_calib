# Frontend and Dashboard

The frontend makes the step-level confidence visible. It has two views: the **Ask** view, where a user submits a question and sees the answer, its confidence and everything behind it, and the **Analytics** view, which visualises every run stored in `calibration_runs.json`. Both are built with React 19 and the Recharts charting library and are served by Vite (Chapter 12). This chapter describes what each view shows and why, and the design rules applied to colour, accessibility and layout. All screenshots were taken from the running application; the Ask-view screenshots answer the question with a real stored response, as explained in @sec:fe-screenshots.

## Design Goals {#sec:fe-goals}

Three goals shaped the interface.

1. **Show where confidence comes from.** A single percentage invites over-trust. Every score is accompanied by the signals that produced it, and the user can drill down from the answer to a step to the evidence for that step.
2. **Point at the weak step.** The predicted error step is the project's main output beyond the answer itself, so it is highlighted consistently in the chart and in the reasoning chain.
3. **Treat stored and live results identically.** A past run opened from the history must look exactly like a fresh answer. A single normalisation layer (`frontend/src/lib/normalize.js`) converts any of the three pipeline response shapes, and stored records written before the full response was persisted, into one common structure that every component renders.

## Ask View {#sec:fe-ask}

The Ask view (@fig:ui-ask-empty) contains the question input, three example questions (one per pipeline, which fill the input when clicked), a slider for the number of consistency samples K (1–10), and a submit button; `Ctrl+Enter` also submits. Before the first question, three cards explain what each pipeline checks.

![Ask view before a question is submitted.](ui_ask_empty.png){#fig:ui-ask-empty}

While a question is being answered, a progress card cycles through the stages a question goes through (routing, generating, sampling, verifying, calibrating). These messages advance on a timer and are indicative only; the backend does not stream progress. A failed request shows an inline alert with the server's error message and a Retry button; when the backend cannot be reached at all, the alert says so explicitly, including the possibility that the page's origin is not allowed by the server's cross-origin policy.

When the answer arrives (@fig:ui-ask-arith), the result is laid out from summary to detail:

- **Answer card.** The pipeline that answered (with its icon), the calibration-status label, the question, the answer, and an animated semicircular **confidence gauge**. The gauge's arc, number and label use three bands: *High* (≥ 75%), *Moderate* (50–75%) and *Low* (< 50%). Thin ticks on the gauge mark the two band boundaries.
- **Summary tiles.** Number of reasoning steps, the weakest step's confidence, the claim verdicts (counts of supported, contradicted and unverified claims, each with its icon) or the flagged step, and the number of distinct sources consulted.
- **Confidence by step.** A bar chart of each step's confidence on a 0–100% axis. A dashed line marks the answer confidence. The predicted error step is drawn in red and labelled *flagged* when it comes from the pipeline, or *weakest* when it is simply the lowest bar. Clicking a bar scrolls to that step.
- **Signal breakdown.** A grouped bar chart of the raw signals of every step (for example verification, consistency and sample agreement for arithmetic), so the user can see *why* a step scored low.
- **Reasoning chain.** A vertical timeline with one card per step or claim. Each card shows the step text, its confidence and band, its type, its verdict, the predicted-error badge if applicable, the number of sources, and a meter for each signal. *Show details* reveals the verifier's rationale, entropy values and sample count, the premises and rules used (logical), and the list of sources with their domain, title and reliability (factual).

![Result of an arithmetic question in the Ask view: confidence gauge, summary tiles, per-step confidence with the flagged step in red, signal breakdown and the start of the reasoning chain.](ui_ask_arithmetic.png){#fig:ui-ask-arith}

For factual answers (@fig:ui-ask-factual) the step cards carry the claim verdict and the sources. For logical answers (@fig:ui-ask-logical) a **Knowledge base** panel lists the premises and the rules in "conditions → conclusion" form, highlights the premises and rules used by the proof, and shows whether the premises were found consistent.

![Reasoning chain of a factual answer. Each claim shows its verdict and signals; the first claim is expanded to show its sources and their reliability.](ui_ask_factual.png){#fig:ui-ask-factual}

![Proof steps of a logical answer and the knowledge base, with the premises and rules used by the proof highlighted.](ui_ask_logical.png){#fig:ui-ask-logical}

A **JSON** tab beside the visual breakdown shows the raw response as a collapsible, colour-coded tree with search (matching keys and values are highlighted and their branches expanded), *Expand all*, *Collapse* and *Copy* buttons, and the size of the document (@fig:ui-json). It exists so that a researcher can see every field, including those not visualised, without leaving the interface.

![Raw JSON view of a stored factual run, with search and expand/collapse controls.](ui_json_view.png){#fig:ui-json}

Answers given during the current session are kept as chips under the input (up to eight), each showing the question, the pipeline colour and the confidence, so earlier answers can be reopened without re-asking.

## Analytics View {#sec:fe-analytics}

The Analytics view (@fig:ui-analytics) is built from all stored runs, fetched from `GET /api/runs`. If the backend is unavailable, the user can open a copy of `calibration_runs.json` from disk instead; the file is parsed in the browser and never uploaded. A filter bar selects all runs or one pipeline and searches questions and answers; every tile and chart below follows the filter.

- **Summary tiles**: number of runs, average confidence, steps per run, the share of verified claims that were supported or entailed, and the number of low-confidence runs (below 50%).
- **Answer confidence over time**: one dot per run, coloured by pipeline; clicking a dot opens that run.
- **Confidence distribution**: a histogram of answer confidence in 10% bands, stacked by pipeline.
- **Does confidence decay along the chain?**: average step confidence by position in the reasoning chain, one line per pipeline.
- **Claim verification verdicts**: supported or entailed, contradicted and unverified claims for each pipeline, with factual and logical verdicts grouped by outcome.

![Analytics view: summary tiles and charts over all stored runs.](ui_analytics.png){#fig:ui-analytics}

Below the charts, the **run history** (@fig:ui-history) lists every run with its question (two lines at most), answer, pipeline, a confidence bar and value, the number of steps and the time. Clicking a row, or pressing Enter on it, opens the run in the same detailed view as a live answer (@fig:ui-dark).

![Run history in the Analytics view.](ui_run_history.png){#fig:ui-history}

![A stored factual run opened from the history, in dark mode.](ui_dark_detail.png){#fig:ui-dark}

## Colour, Accessibility and Layout {#sec:fe-accessibility}

**Colour by role.** Colours are assigned by the job they do, never decoratively. The three pipelines use fixed categorical colours (blue for arithmetic, orange for factual, aqua for logical) taken, in order, from a colour-blind-safe palette whose adjacent colours were checked for separation under simulated colour-vision deficiency. Status colours (green, amber, red) are reserved for verdicts and confidence bands and never reused for a category. A status is never shown by colour alone: every status pill carries an icon and a word (✓ Supported, ✕ Contradicted, ? Unverified; ▲ High, ■ Moderate, ▼ Low). Text always uses the normal text colours; the coloured mark beside it carries the identity.

**Themes.** The interface has light and dark themes. By default it follows the operating-system setting; a button in the top bar cycles between *system*, *light* and *dark*, and the choice is remembered in the browser. The dark theme is a separately chosen set of colours rather than an automatic inversion, and the charts read their colours from the same theme variables, so they switch with the page.

**Layout.** The layout adapts down to phone width (@fig:ui-mobile): grids collapse to one column, the gauge moves below the answer, the submit button spans the width, and wide tables scroll horizontally within their own scrollable area. Animations are short and are disabled when the user's system requests reduced motion.

![Phone-width layout (400 px wide) of an arithmetic answer: answer card, gauge, tiles and charts stacked in one column.](ui_mobile.png){#fig:ui-mobile}

## Screenshot Method {#sec:fe-screenshots}

The screenshots in this chapter were captured with headless Chrome driven through the DevTools protocol by `report/scripts/screenshots.mjs`. To avoid spending API credits and to make the figures reproducible, the Ask-view screenshots intercept the browser's `POST /api/ask` request and answer it with the stored `pipeline_output` of a real run from `calibration_runs.json` (run 21 for arithmetic, 15 for factual and 29 for logical, counting from 1). The interface code path is exactly the one used for a live answer. The Analytics screenshots use the live backend's `GET /api/runs`. Full-page captures are kept in `report/figures/raw/`, and `crop_screenshots.py` crops each figure to the region it discusses.
