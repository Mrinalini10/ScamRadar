#!/usr/bin/env bash
# ScamRadar — One-command setup and run
# Usage: bash setup.sh

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo ""
echo -e "${CYAN}  ███████╗ ██████╗ █████╗ ███╗   ███╗██████╗  █████╗ ██████╗  █████╗ ██████╗ ${NC}"
echo -e "${CYAN}  ██╔════╝██╔════╝██╔══██╗████╗ ████║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗${NC}"
echo -e "${CYAN}  ███████╗██║     ███████║██╔████╔██║██████╔╝███████║██║  ██║███████║██████╔╝${NC}"
echo -e "${CYAN}  ╚════██║██║     ██╔══██║██║╚██╔╝██║██╔══██╗██╔══██║██║  ██║██╔══██║██╔══██╗${NC}"
echo -e "${CYAN}  ███████║╚██████╗██║  ██║██║ ╚═╝ ██║██║  ██║██║  ██║██████╔╝██║  ██║██║  ██║${NC}"
echo -e "${CYAN}  ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝${NC}"
echo ""
echo -e "  ${YELLOW}Scam Genomic Surveillance System${NC}"
echo ""

# ─── Backend ────────────────────────────────────────────────────────────────

echo -e "${GREEN}[1/4] Setting up Python backend...${NC}"
cd "$BACKEND"

if [ ! -d "venv" ]; then
  echo "  Creating virtual environment..."
  python3 -m venv venv
fi

echo "  Activating virtual environment..."
source venv/bin/activate

echo "  Installing Python dependencies (this may take 2-3 minutes first time)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "${GREEN}[2/4] Fetching and preparing dataset...${NC}"
python3 -c "from ml.dataset import preprocess_and_save; preprocess_and_save()"

# ─── Frontend ────────────────────────────────────────────────────────────────

echo -e "${GREEN}[3/4] Setting up React frontend...${NC}"
cd "$FRONTEND"
npm install --legacy-peer-deps --cache /tmp/npm-cache-scamradar --silent

# ─── Launch both servers ─────────────────────────────────────────────────────

echo -e "${GREEN}[4/4] Launching ScamRadar...${NC}"
echo ""
echo -e "  ${CYAN}Backend  →  http://localhost:8000${NC}"
echo -e "  ${CYAN}Frontend →  http://localhost:5173${NC}"
echo -e "  ${CYAN}API Docs →  http://localhost:8000/docs${NC}"
echo ""
echo -e "  ${YELLOW}Quick start:${NC}"
echo -e "  1. Open http://localhost:5173"
echo -e "  2. Click 'Dataset Loader' in sidebar → 'Load Dataset'"
echo -e "  3. Wait ~1 min for ingestion, then explore Dashboard"
echo ""

# Start backend in background
cd "$BACKEND"
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend (foreground — Ctrl+C stops both)
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}✅ Both servers running. Press Ctrl+C to stop.${NC}"

# Wait and clean up on exit
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
