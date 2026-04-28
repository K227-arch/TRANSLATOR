#!/bin/bash
# Start both backend and frontend for production

set -e

echo "Starting Lunyoro-Rutooro Translator..."

# Backend
cd backend
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID) on port ${PORT:-8000}"

# Frontend
cd ../frontend
npm start &
FRONTEND_PID=$!
echo "Frontend started (PID $FRONTEND_PID) on port 3000"

# Wait for both
wait $BACKEND_PID $FRONTEND_PID
