#!/usr/bin/env bash
# install_linux.sh: Linux installer and launch script creator for SDRGuardian
set -e
# Determine project root (one level up from scripts dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 1. Create Python virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# 2. Activate and install dependencies
echo "Activating virtual environment and installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Dependencies installed in .venv."

# 3. Create launch scripts
cat << 'EOF' > launch_gui.sh
#!/usr/bin/env bash
# Launch the SDRGuardian GUI
cd "$(dirname "$0")"
source .venv/bin/activate
python run.py --mode gui
EOF
chmod +x launch_gui.sh
echo "Created launch_gui.sh. Run to start the GUI."

cat << 'EOF' > launch_pipeline.sh
#!/usr/bin/env bash
# Launch the SDRGuardian pipeline (prints sensor data)
cd "$(dirname "$0")"
source .venv/bin/activate
python run.py --mode pipeline
EOF
chmod +x launch_pipeline.sh
echo "Created launch_pipeline.sh. Run to start the pipeline."

echo "To install as a systemd service, see sdrguardian.service.example in the project root."

# 4. Ensure Ollama CLI is installed
if ! command -v ollama &>/dev/null; then
  echo "Ollama CLI not found. Attempting to install..."
  if command -v brew &>/dev/null; then
    echo "Installing Ollama via Homebrew..."
    brew install ollama
  elif command -v apt-get &>/dev/null; then
    echo "Installing Ollama via apt-get..."
    sudo apt-get update && sudo apt-get install -y ollama
  elif command -v snap &>/dev/null; then
    echo "Installing Ollama via snap..."
    sudo snap install ollama
  else
    echo "Error: Ollama CLI not found and no known package manager."
    echo "Please install Ollama manually from https://ollama.com"
  fi
fi

# 5. Ensure default Ollama model and server
if command -v ollama &>/dev/null; then
  echo "Ensuring default Ollama model 'llama3.2:latest' is installed..."
  if ! ollama list llms | grep -q '^llama3\.2:latest'; then
    echo "Pulling llama3.2:latest..."
    ollama pull llama3.2:latest
  fi
  if ! pgrep -f "ollama serve" >/dev/null; then
    echo "Starting Ollama server in background..."
    nohup ollama serve &>/dev/null &
  else
    echo "Ollama server is already running."
  fi
else
  echo "Skipping model pull and server start since Ollama CLI is not installed."
fi