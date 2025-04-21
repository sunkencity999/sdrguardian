#!/usr/bin/env python3
import subprocess
import re

def test_wifi_parser():
    """Test different parsing approaches for system_profiler output"""
    print("===== WiFi Parser Test =====")
    
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
    
    # Save the raw output to a file for inspection
    with open("system_profiler_output.txt", "w") as f:
        f.write(output)
    print("Saved raw output to system_profiler_output.txt")
    
    # Parse using a line-by-line approach with state tracking
    print("\n=== Line-by-line Parsing ===")
    networks = []
    
    lines = output.splitlines()
    in_networks_section = False
    current_network = None
    
    for i, line in enumerate(lines):
        # Check if we're entering the networks section
        if "Other Local Wi-Fi Networks:" in line:
            in_networks_section = True
            print(f"Found networks section at line {i}")
            continue
        
        # Process lines in the networks section
        if in_networks_section:
            # Look for network names (indented with exactly 12 spaces and ending with colon)
            if line.startswith("            ") and line.strip().endswith(":"):
                # Skip property lines like "Channel:" or "Security:"
                if not any(prop in line for prop in ["Channel:", "Security:", "PHY Mode:", "Network Type:"]):
                    ssid = line.strip().rstrip(':')
                    print(f"Line {i}: Found potential network: '{ssid}'")
                    
                    # Check the next few lines to confirm this is a network entry
                    is_network = False
                    for j in range(1, 5):
                        if i + j < len(lines):
                            next_line = lines[i + j]
                            if "PHY Mode:" in next_line:
                                is_network = True
                                break
                    
                    if is_network:
                        networks.append(ssid)
                        print(f"Confirmed network: {ssid}")
    
    print(f"\nFound {len(networks)} networks:")
    for i, network in enumerate(networks):
        print(f"  {i+1}. {network}")
    
    # Also check for current network
    print("\n=== Current Network ===")
    current_network_section = False
    current_ssid = None
    
    for i, line in enumerate(lines):
        if "Current Network Information:" in line:
            current_network_section = True
            print(f"Found current network section at line {i}")
            continue
        
        if current_network_section and line.startswith("            ") and line.strip().endswith(":"):
            if not any(prop in line for prop in ["Channel:", "Security:", "PHY Mode:", "Network Type:"]):
                current_ssid = line.strip().rstrip(':')
                print(f"Current network: {current_ssid}")
                break

if __name__ == "__main__":
    test_wifi_parser()
