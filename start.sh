#!/bin/bash

# Kill background processes on exit
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# Start Backend
echo "Starting Backend..."
python3 backend/main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start Frontend
echo "Starting Frontend..."
cd frontend && npm run dev

wait $BACKEND_PID
