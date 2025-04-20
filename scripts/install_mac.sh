#!/usr/bin/env bash
# install_mac.sh: macOS installer and launch script creator for SDRGuardian
set -e
# Ensure script runs under bash
if [ -z "$BASH_VERSION" ]; then
  echo "Re-executing under bash under current shell..."
  exec bash "$0" "$@"
fi
# Determine project root (one level up from scripts dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
# install_mac.sh: macOS installer and launch script creator for SDRGuardian
set -e

# 1. Create Python virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

## 2. Activate and install dependencies
echo "Activating virtual environment and installing dependencies..."
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Dependencies installed in .venv."

# 3. Create launch scripts
cat << 'EOF' > launch_gui.command
#!/usr/bin/env bash
# Launch the SDRGuardian GUI
cd "$(dirname "$0")"
. .venv/bin/activate
python run.py --mode gui
EOF
chmod +x launch_gui.command
echo "Created launch_gui.command. Double-click or run to start the GUI."

cat << 'EOF' > launch_pipeline.command
#!/usr/bin/env bash
# Launch the SDRGuardian pipeline (prints sensor data)
cd "$(dirname "$0")"
. .venv/bin/activate
python run.py --mode pipeline
EOF
chmod +x launch_pipeline.command
echo "Created launch_pipeline.command. Run to start the pipeline."

# 4. Ensure Ollama CLI is installed
if ! command -v ollama &>/dev/null; then
  if command -v brew &>/dev/null; then
    echo "Ollama CLI not found; installing via Homebrew..."
    brew install ollama
  else
    echo "Error: Ollama CLI not found and Homebrew unavailable."
    echo "Please install Ollama manually: https://ollama.com"
  fi
fi

# 5. Ensure default model and Ollama server
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