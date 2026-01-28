#!/bin/bash

# Get the directory where the script is located
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"
SCRIPT_PATH="$PROJECT_DIR/financial_dashboard/dashboard.py"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
PORT=8599
URL="http://127.0.0.1:$PORT"
LOG_FILE="$PROJECT_DIR/startup_error.log"

echo "Project Directory: $PROJECT_DIR"
echo "------------------------------"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed (or not in PATH)."
    echo "Please download and install Python 3 from python.org"
    read -p "Press Enter to exit..."
    exit 1
fi

# 2. Setup Virtual Environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Setting up environment (first run, may take a minute)..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"
    echo "Setup complete."
fi

# 3. Check if Port is already in use
if lsof -i :$PORT > /dev/null; then
    echo "WARNING: Port $PORT is busy. Killing old process..."
    lsof -ti :$PORT | xargs kill -9
    sleep 1
fi

# 4. Start Dashboard
echo "Starting Dashboard on $URL..."
echo "Logging output to $LOG_FILE"

# Start Streamlit in BACKGROUND
"$VENV_DIR/bin/streamlit" run "$SCRIPT_PATH" --server.port $PORT --server.address 127.0.0.1 --server.headless true > "$LOG_FILE" 2>&1 &
PID=$!

# 5. Wait for Port to be Active (Netcat Loop)
echo "Waiting for server to initialize..."
MAX_RETRIES=30
COUNT=0

while ! nc -z 127.0.0.1 $PORT; do   
  sleep 1
  COUNT=$((COUNT+1))
  
  # check if process died
  if ! kill -0 $PID > /dev/null 2>&1; then
      echo "------------------------------"
      echo "ERROR: Server process died unexpectedly."
      echo "Check 'startup_error.log' for details."
      cat "$LOG_FILE"
      echo "------------------------------"
      read -p "Press Enter to exit..."
      exit 1
  fi
  
  if [ $COUNT -ge $MAX_RETRIES ]; then
      echo "------------------------------"
      echo "TIMEOUT: Server took too long to start."
      echo "Please check 'startup_error.log'."
      echo "------------------------------"
      read -p "Press Enter to exit..."
      exit 1
  fi
done

echo "Server is UP! Opening browser..."
open "$URL"

# Keep script running
wait $PID
