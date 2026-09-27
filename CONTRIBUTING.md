Now don't run everything at once

Your GSM8K part is already working. Do not touch it.

First verify only the backend.

From your current directory:

~/fun/mvp/ai-confidence-calibration

run:

python -m pip install -r requirements.txt

Then:

PYTHONPATH=backend python -c "from app.main import app; print(app.title)"

Expected:

AI Confidence Calibration

Then:

python -m uvicorn app.main:app --reload --port 8000 --app-dir backend

Expected:

INFO:     Uvicorn running on http://127.0.0.1:8000

Then open:

http://127.0.0.1:8000/docs

You should see these API groups:

health
questions
inference
evaluation
After that

Test the health endpoint:

http://127.0.0.1:8000/api/health

Expected:

{
  "status": "ok"
}

Then test inference from Swagger with:

{
  "question": "Janet has 16 eggs. She eats 3 and uses 4 for muffins. She sells each remaining egg for $2. How much does she make?",
  "num_consistency_samples": 5
}

At this stage, the answer will still be a mock answer. That's intentional.

Once that works, the next serious research step is replacing:

Mock LLM

with the actual LLM reasoning generator, and then implementing genuine:

K = 5 prefix-conditioned samples

rather than the current placeholder. That's where your actual FYP methodology starts becoming experimental rather than just software scaffolding.