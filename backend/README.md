
# Backend setup

Install the backend dependencies, then copy the repository-root `.env.example`
to `.env` and set `LLM_API_KEY` to your OpenAI API key. The default provider
and model are already configured. The factual pipeline uses that same key for
web search and evidence assessment, so no separate search-provider key is
required. No other environment settings are required for inference.

Run the API from this directory with:

```powershell
python -m uvicorn app.main:app --reload
```
