# Technology Stack

This chapter lists the languages, frameworks, libraries and services that Calibra is built on, with the versions installed in the development environment used for every result in this report, and explains why each was chosen. Declared version ranges come from `backend/requirements.txt`, the root `requirements.txt` and `frontend/package.json`; the installed versions were read from the project's virtual environment and `node_modules`.

## Languages and Runtimes {#sec:stack-languages}

@tab:stack-languages lists the languages and runtimes used.

Table: Languages and runtimes. {#tab:stack-languages}

| Component | Version | Used for |
|---|---|---|
| Python | 3.13.0 | Backend, all three pipelines, experiments, analysis scripts |
| JavaScript (ES modules, JSX) | — | Frontend |
| Node.js | 24.14.1 | Frontend tooling (Vite), report figure and screenshot scripts |
| Git | 2.49.0 | Version control |

Python was the natural choice for the backend because the model SDK, the SMT solver, gradient boosting and the dataset tooling all have first-class Python libraries. The frontend is a separate JavaScript application so that it can be developed, built and deployed independently of the API.

## Backend {#sec:stack-backend}

@tab:stack-backend lists the backend libraries with the version range declared in the requirements files and the version installed.

Table: Backend libraries. {#tab:stack-backend}

| Library | Declared | Installed | Role |
|---|---|---|---|
| FastAPI | ≥ 0.115, < 1 | 0.141.1 | HTTP API, request validation, OpenAPI schema |
| Starlette | (FastAPI dependency) | 1.7.0 | ASGI toolkit underlying FastAPI; CORS middleware |
| Uvicorn | ≥ 0.30, < 1 | 0.54.0 | ASGI server |
| Pydantic | ≥ 2.8, < 3 | 2.13.5 | Request/response models, structured-output schemas |
| pydantic-settings | ≥ 2.4, < 3 | 2.15.0 | Configuration from `.env` |
| python-dotenv | unpinned | 1.2.3 | `.env` loading |
| OpenAI Python SDK | ≥ 2.0, < 3 | 2.54.0 | Chat completions, log-probabilities, Responses API with web search |
| httpx | ≥ 0.27, < 1 | 0.28.1 | Fetching cited web pages; test client |
| z3-solver | ≥ 4.13, < 5 | 4.16.0.0 | SMT solving for the logical pipeline |
| XGBoost | ≥ 2.1, < 4 | 3.4.1 | Trainable step calibrator |
| scikit-learn | ≥ 1.5, < 2 | 1.9.1 | Grouped train/test splitting for the calibrator |
| NumPy | ≥ 1.26, < 3 | 2.5.3 | Numerical support |
| pandas | ≥ 2, < 4 | 3.0.5 | Data handling in experiments |
| Hugging Face Datasets | ≥ 3, < 5 | 5.0.1 | Loading GSM8K, TriviaQA and RuleTaker |
| SQLAlchemy, psycopg | ≥ 2.0; ≥ 3.2 | 2.1.1; 3.3.6 | Declared for a future relational store; not used by the current JSON run store |
| pytest | — | 9.1.1 | Test runner |

**FastAPI** was chosen for its declarative request validation with Pydantic: the constraints on a request (a non-empty question, between 1 and 10 samples) are written once, in the model, and enforced before any pipeline code runs. **Pydantic** is also used to generate the JSON schema for the gateway classifier's structured output, so the classifier's allowed categories and the router's expectations come from the same definition.

The **OpenAI SDK** provides three features the pipelines depend on: JSON-mode and strict JSON-schema output (so responses can be parsed and validated rather than scraped from free text), several samples per request with per-token log-probabilities and top alternatives (used for next-step sampling and token statistics), and the Responses API with a web-search tool that returns cited URLs (used for factual retrieval).

**Z3** [@demoura2008] was chosen over a hand-written logic engine because it is a complete, well-tested decision procedure for the fragment of first-order logic that the logical pipeline needs (uninterpreted functions, quantifiers over a finite set of constants), it reports unsatisfiable cores, which give the premises and rules a proof used, and it supports timeouts so that a pathological input cannot hang the API.

**XGBoost** [@chen2016] was chosen for the step calibrator because it works well on small tabular data, handles missing features natively, and produces probabilities that can then be evaluated with the calibration metrics. **scikit-learn** provides the grouped shuffle split used to keep the steps of one question on one side of the train/test split.

## Frontend {#sec:stack-frontend}

@tab:stack-frontend lists the frontend libraries.

Table: Frontend libraries. {#tab:stack-frontend}

| Library | Declared | Installed | Role |
|---|---|---|---|
| React, React DOM | ^19.0.0 | 19.3.0 | User interface |
| Recharts | ^2.15.0 | 2.15.4 | Charts in the Ask and Analytics views |
| axios | ^1.8.0 | 1.20.0 | HTTP client for the API |
| Vite | ^6.0.0 | 6.4.3 | Development server and production build |
| @vitejs/plugin-react | ^4.4.0 | 4.7.0 | JSX transform and fast refresh for Vite |

**React** keeps the interface a function of the current state (question, result, selected step), which suits a view that re-renders the same result in several linked components: the chart, the timeline and the summary tiles. **Recharts** provides declarative SVG charts with built-in tooltips and click events, used for the per-step charts and the analytics charts; colours are passed in from the theme so that charts follow light and dark mode. **Vite** gives a fast development server and an optimised production build; the API base URL is configurable with the `VITE_API_BASE_URL` environment variable. The interface itself uses no component library: styling is plain CSS with custom properties for the theme.

## External Services {#sec:stack-services}

@tab:stack-services lists the external services the system depends on.

Table: External services. {#tab:stack-services}

| Service | Model / endpoint | Used by |
|---|---|---|
| OpenAI Chat Completions | `gpt-4o-mini` | Classification, generation, next-step sampling, step verification, claim assessment |
| OpenAI Responses API, `web_search` tool | `gpt-4.1-mini` | Factual retrieval |
| Public web | HTTP(S) page fetch | Replacing low-relevance search excerpts with page text |
| Hugging Face Hub | dataset download | `openai/gsm8k`, `mandarjoshi/trivia_qa`, `tasksource/ruletaker` for the pilots |

All three model-facing operations are behind the single `LLMService` class, so changing the model or provider affects one file. The provider is currently restricted to OpenAI; the class raises a clear error for any other value.

## Configuration {#sec:stack-config}

The backend reads its configuration from a `.env` file at the repository root through pydantic-settings; the variables and defaults are listed in @tab:config. Settings are loaded once and cached. The API key is never logged or returned. The frontend's only setting is the API base URL. Secrets are excluded from version control by `.gitignore`, as are the run store and generated build output.

## Development Environment {#sec:stack-dev}

Development and all experiments were carried out on a Windows 11 workstation. The backend runs in a Python virtual environment (`venv/`) and the frontend in its own `node_modules`. No GPU is required, because all model inference is hosted. The project is versioned with Git; the history at the time of writing contains five commits between 27 September and 19 November 2026 (Appendix F), with later changes in the working tree. Jupyter notebooks under `notebooks/` were used for early exploration of GSM8K, the signals, and evaluation.

The report itself is generated from the repository: Markdown sources in `report/md/`, figures produced by scripts in `report/scripts/` (matplotlib for data charts, Mermaid rendered in headless Chrome for diagrams, Chrome DevTools automation for screenshots), metrics computed from the stored results by `compute_metrics.py`, and the Word document assembled by `build_docx.py` using python-docx, with LibreOffice used to convert it to PDF for page numbering.
