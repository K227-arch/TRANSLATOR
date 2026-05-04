#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Lunyoro-Rutooro Translator — Full Setup Script (Linux/macOS)
# ─────────────────────────────────────────────────────────────
set -e

echo "=== Lunyoro-Rutooro Translator Setup ==="

# ── 1. Python dependencies ────────────────────────────────────
echo ""
echo "[1/5] Installing Python dependencies..."
pip install -r backend/requirements.txt

# ── 2. Node dependencies ──────────────────────────────────────
echo ""
echo "[2/5] Installing frontend dependencies..."
cd frontend && npm install && cd ..

# ── 3. Download models from HuggingFace ──────────────────────
echo ""
echo "[3/5] Downloading translation models from HuggingFace..."
python backend/download_models.py

# ── 4. Ollama / Qwen setup ────────────────────────────────────
echo ""
echo "[4/5] Setting up Ollama (LLM for chat)..."
if ! command -v ollama &> /dev/null; then
    echo "  Ollama not found. Install it from https://ollama.com/download then run:"
    echo "    ollama pull qwen2.5:3b"
else
    echo "  Pulling qwen2.5:3b model (~2GB)..."
    ollama pull qwen2.5:3b || echo "  WARNING: Could not pull qwen2.5:3b. Run manually: ollama pull qwen2.5:3b"
fi

# ── 5. Done ───────────────────────────────────────────────────
echo ""
echo "[5/5] Setup complete!"
echo ""
echo "To run the app:"
echo "  Terminal 1 (backend):  cd backend && uvicorn main:app --reload --port 8000"
echo "  Terminal 2 (frontend): cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3002"
