#!/bin/bash

# Get the directory where the script is located
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"
SCRIPT_PATH="$PROJECT_DIR/financial_dashboard/dashboard.py"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
PORT=8504
URL="http://localhost:$PORT"

echo "Project Directory: $PROJECT_DIR"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed (or not in PATH)."
    echo "Please download and install Python 3 from python.org"
    exit 1
fi

# 2. Setup Virtual Environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Setting up environment (first run)..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"
    echo "Setup complete."
fi

# 3. Check if Streamlit is running
if lsof -i :$PORT > /dev/null; then
    echo "Dashboard is already running on port $PORT."
    open "$URL"
    exit 0
fi

# 4. Start Dashboard
echo "Starting Dashboard on $URL..."
# Run in background (nohup) so terminal can be closed if desired, 
# but logging locally.
nohup "$VENV_DIR/bin/streamlit" run "$SCRIPT_PATH" --server.port $PORT --server.headless true > "$PROJECT_DIR/dashboard.log" 2>&1 &

# Wait for boot
sleep 2
open "$URL"
