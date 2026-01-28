#!/bin/bash
cd "$(dirname "$0")"

# Kill existing streamlit processes
pkill -f streamlit || true

# Activate venv if needed or just use direct path
VENV_PYTHON="./venv/bin/python3"
VENV_STREAMLIT="./venv/bin/streamlit"

echo "Starting Regular Dashboard (Version 28) on Port 8501..."
nohup $VENV_STREAMLIT run financial_dashboard/dashboard.py --server.port 8501 --server.headless true > dashboard_regular.log 2>&1 &

echo "Starting Demo Dashboard (Version 28) on Port 8502..."
nohup $VENV_STREAMLIT run financial_dashboard/dashboard_demo.py --server.port 8502 --server.headless true > dashboard_demo.log 2>&1 &

sleep 3

echo "Regular Dashboard: http://localhost:8501"
echo "Demo Dashboard:    http://localhost:8502"
open http://localhost:8501
open http://localhost:8502
