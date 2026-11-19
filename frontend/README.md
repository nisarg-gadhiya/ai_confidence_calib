# Frontend

Start the backend from the repository root in one PowerShell terminal:

```powershell
.\venv\Scripts\Activate.ps1
Set-Location backend
python -m uvicorn app.main:app --reload
```

In another terminal, start the frontend:

```powershell
Set-Location frontend
npm run dev
```

Open `http://localhost:5173`. The frontend sends questions to the gateway at
`http://127.0.0.1:8000/api/ask`. Set `VITE_API_BASE_URL` to override the API
base URL.

The answer and confidence are shown in the UI. Step-level calibration is stored
on the backend in `backend/data/calibration_runs.json` after each successful
gateway response; that local data file is ignored by Git. Each record keeps the
complete response under `pipeline_output`; factual source URLs are also listed
with their calibration steps.
## Views

- **Ask** (`/`): submit a question and see the answer with a confidence gauge,
  per-step confidence and signal charts, the reasoning chain (verdicts,
  sources, rationale), the premise/rule base for logical questions, and an
  interactive JSON viewer for the raw response.
- **Analytics** (`/#analytics`): charts and a searchable run history built
  from `backend/data/calibration_runs.json`, served by `GET /api/runs`. If the
  backend is not running, use **Open JSON file…** to load the file directly.
  Click any run to open it in the same detailed view.
