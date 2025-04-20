#!/usr/bin/env bash
# Launch the SDRGuardian pipeline (prints sensor data)
cd "$(dirname "$0")"
. .venv/bin/activate
python run.py --mode pipeline
