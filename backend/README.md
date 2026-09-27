
# Backend setup

Install the backend dependencies, then copy the repository-root `.env.example`
to `.env` and set `LLM_API_KEY` to your OpenAI API key. The default provider
and model are already configured; no other environment settings are required
for inference.

Run the API from this directory with:

```powershell
python -m uvicorn app.main:app --reload
```
