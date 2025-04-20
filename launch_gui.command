#!/usr/bin/env bash
# Launch the SDRGuardian GUI
cd "$(dirname "$0")"
. .venv/bin/activate
python run.py --mode gui
