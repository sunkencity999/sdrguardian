#!/usr/bin/env python3
import subprocess
import re

def test_direct_wifi():
    """Direct test of WiFi scanning using system_profiler"""
    print("===== Direct WiFi Test =====")
    
    # Run system_profiler directly
    print("Running system_profiler SPAirPortDataType...")
    result = subprocess.run(
        ["system_profiler", "SPAirPortDataType"],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Check if command succeeded
    if result.returncode != 0:
        print(f"Error running system_profiler: {result.stderr}")
        return
    
    output = result.stdout
    print(f"Output length: {len(output)} characters")
    
    # Check for current network
    if "Current Network Information:" in output:
        print("Found 'Current Network Information' section")
    else:
        print("No 'Current Network Information' section found")
    
    # Check for other networks
    if "Other Local Wi-Fi Networks:" in output:
        print("Found 'Other Local Wi-Fi Networks' section")
        
        # Extract network names using a simpler approach
        # Look for lines with exactly 12 spaces followed by a name and colon
        networks = re.findall(r"            ([\w-]+):", output)
        
        print(f"Found {len(networks)} networks:")
        for i, network in enumerate(networks):
            print(f"  {i+1}. {network}")
    else:
        print("No 'Other Local Wi-Fi Networks' section found")

if __name__ == "__main__":
    test_direct_wifi()
