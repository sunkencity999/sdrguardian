#!/usr/bin/env python3
"""
SDRGuardian Sudo Wrapper

This script ensures that the SDRGuardian application runs with sudo privileges,
which are required for certain sensor operations like WiFi scanning with wdutil.
"""

import os
import sys
import subprocess
import getpass

def check_sudo():
    """Check if the script is running with sudo privileges."""
    return os.geteuid() == 0

def run_with_sudo():
    """Run the application with sudo privileges."""
    if check_sudo():
        print("Running with sudo privileges...")
        # We already have sudo, just run the main script
        import run
        run.main()
    else:
        print("SDRGuardian requires sudo privileges for certain sensor operations.")
        print("Please enter your sudo password when prompted.")
        
        # Get command line arguments to pass to the main script
        args = sys.argv[1:]
        cmd_args = " ".join(args)
        
        try:
            # Use sudo to run this same script (which will then have sudo privileges)
            cmd = f"sudo {sys.executable} {__file__} {cmd_args}"
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running with sudo: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(1)

def main():
    """Main entry point for the sudo wrapper."""
    # Store sudo password in environment variable for sensors to use
    if check_sudo() and 'SUDO_PASSWORD' not in os.environ:
        # If we're running as sudo but don't have the password stored,
        # we might need to ask for it to pass to sensors
        try:
            sudo_password = getpass.getpass("Enter sudo password for sensors: ")
            os.environ['SUDO_PASSWORD'] = sudo_password
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(1)
    
    # Import and run the main application
    import run
    run.main()

if __name__ == "__main__":
    run_with_sudo()
