# Lunyoro / Rutooro Translator

## Setup & Run

### Backend (Python)

```bash
cd backend
pip install -r requirements.txt

# Build the translation index (run once)
python train.py

# Start the API server
python -m uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## How it works

1. `train.py` encodes all 6,246 English sentences using a multilingual sentence transformer
2. At query time, your input is encoded and matched against the closest sentence
3. Falls back to dictionary word lookup if no close match found
4. All translations are saved to `backend/history.json`
