#!/bin/bash
# SDRGuardian macOS Launcher
# This script launches SDRGuardian with sudo privileges
# Double-click this file in Finder to run the application

# Set terminal title
echo -e "\033]0;SDRGuardian\007"

# Print a nice header
echo "========================================="
echo "     SDRGuardian - Military Edition      "
echo "========================================="
echo

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if we're running with sudo already
if [ "$EUID" -ne 0 ]; then
    echo "SDRGuardian requires sudo privileges for certain sensor operations."
    echo "Please enter your sudo password when prompted."
    echo
    
    # Re-run this script with sudo
    sudo "$0" "$@"
    exit $?
fi

# We're running with sudo now
echo "Starting SDRGuardian with sudo privileges..."
echo "Application logs will appear below:"
echo "----------------------------------------"
echo

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run the Python script in GUI mode by default if no arguments are provided
if [ $# -eq 0 ]; then
    echo "Starting in GUI mode..."
    python run.py --mode gui
else
    python run.py "$@"
fi

# Keep the terminal window open after the script finishes
echo
echo "----------------------------------------"
echo "SDRGuardian has exited. Press any key to close this window."
read -n 1 -s
