.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Set-Location backend
python -m uvicorn app.main:app --reload