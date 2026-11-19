# Reproducing the Results

This appendix gives the exact commands to set up Calibra, run it, run the tests and pilots, and regenerate every number, figure and document in this report. Commands are for Windows PowerShell, run from the repository root unless stated otherwise; they work in a POSIX shell with the usual changes to paths and environment-variable syntax.

## Setting Up

```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
```

Create a file named `.env` in the repository root containing at least:

```
LLM_API_KEY=<your OpenAI API key>
LLM_MODEL=gpt-4o-mini
FACTUAL_SEARCH_MODEL=gpt-4.1-mini
CONSISTENCY_SAMPLES=5
```

## Running the Application

```
# terminal 1: API on http://127.0.0.1:8000
.\venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload

# terminal 2: frontend on http://localhost:5173
cd frontend
npm run dev
```

Open `http://localhost:5173` for the Ask view and `http://localhost:5173/#analytics` for the Analytics view. Every answered question is appended to `backend/data/calibration_runs.json`.

## Running the Tests

```
.\venv\Scripts\python.exe -m pytest tests -q
```

No API key or network access is needed; all model and web calls are stubbed (Chapter 15).

## Running the Pilots

The pilots make paid API calls. Each script loads its dataset from the Hugging Face Hub and writes its results under the pipeline's `experiments/results/` directory.

```
.\venv\Scripts\python.exe arithmetic\experiments\run_gsm8k_pilot.py
.\venv\Scripts\python.exe factual\experiments\factual_pilot_test.py
.\venv\Scripts\python.exe logical\experiments\logical_pilot_test.py
```

## Training the Step Calibrator

Given labelled step features as JSON lines, `{"question_id": ..., "step_correct": 0 or 1, "features": {...}}`:

```
.\venv\Scripts\python.exe -m arithmetic.experiments.train_step_calibrator `
    --data data\step_features.jsonl --output artifacts\step_calibrator.json
```

Set `STEP_CALIBRATOR_PATH=artifacts/step_calibrator.json` in `.env` to make the API use the trained model.

## Regenerating the Report

The report tooling uses its own virtual environment so that the project environment is not modified.

```
python -m venv report\.venv
report\.venv\Scripts\pip install python-docx matplotlib numpy pandas scikit-learn pymupdf pillow
cd report\tools
npm install mermaid@10.9.1
cd ..\..

# 1. metrics from stored results (project venv: needs the pipelines and Z3)
$env:PYTHONPATH = ".;backend"
.\venv\Scripts\python.exe report\scripts\compute_metrics.py

# 2. data charts and Gantt chart (report venv)
report\.venv\Scripts\python.exe report\scripts\make_charts.py
report\.venv\Scripts\python.exe report\scripts\make_charts.py --gantt

# 3. diagrams from report\diagrams\*.mmd (headless Chrome)
node report\scripts\render_mermaid.mjs

# 4. screenshots (backend on :8000 and frontend dev server on :5180 must be running)
node report\scripts\screenshots.mjs http://localhost:5180/
report\.venv\Scripts\python.exe report\scripts\crop_screenshots.py

# 5. generated appendices (prompts, sample outputs, policy, project record)
report\.venv\Scripts\python.exe report\scripts\gen_appendices.py

# 6. Word document, converted to PDF with LibreOffice for page numbering
report\.venv\Scripts\python.exe report\scripts\build_docx.py --pdf
```

Step 1 makes no model or network calls: it reads the pilot result files, the run store and the test suite. Steps 2 to 6 read only the outputs of the earlier steps and the repository files.
