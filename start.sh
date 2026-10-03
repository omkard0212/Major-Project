#!/bin/bash
echo "Starting ArthSathi..."

# Check .env
if [ ! -f "backend/config/.env" ]; then
    echo "[ERROR] .env not found. Run setup.sh first."
    exit 1
fi

# Start backend
cd backend && python3 app.py &
BACKEND_PID=$!
cd ..

sleep 3

# Start frontend
cd frontend && python3 -m http.server 8080 &
FRONTEND_PID=$!
cd ..

sleep 2

# Open browser
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8080
elif command -v open &> /dev/null; then
    open http://localhost:8080
fi

echo "ArthSathi running at http://localhost:8080"
echo "Press Ctrl+C to stop."

# Keep running until Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
