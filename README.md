# SDRGuardian

SDRGuardian is a Software Defined Radio solution leveraging a laptop's built-in sensors (Wi-Fi, Bluetooth, IMU) combined with local LLM analysis (via Ollama) and a browser GUI for live dashboards and alerts.

## Setup
1. (Option A) Manual setup:
   a. Create and activate a virtual environment:
      ```bash
      python3 -m venv .venv
      source .venv/bin/activate
      ```
   b. Install dependencies:
      ```bash
      pip install -r requirements.txt
      ```
   c. Adjust `config.yaml` to set sensor intervals, LLM model, and alert thresholds.

2. (Option B) Automated installer:
   - On macOS:
     ```bash
     bash scripts/install_mac.sh
     ```
   - On Linux:
     ```bash
     bash scripts/install_linux.sh
     ```
   This will set up the virtual environment, install dependencies, and generate launch scripts.

## Running
After installation, use the generated launch scripts, or run manually:
- Pipeline (collect and print sensor data):
  ```bash
  # Manual
  python run.py --mode pipeline
  # Or use generated script
  ./launch_pipeline.sh     # Linux
  ./launch_pipeline.command # macOS
  ```
- GUI (FastAPI + WebSocket dashboard):
  ```bash
  # Manual
  python run.py --mode gui
  # Or use generated script
  ./launch_gui.sh         # Linux
  ./launch_gui.command     # macOS
  ```

Navigate to http://127.0.0.1:8000 in your browser to view the dashboard.