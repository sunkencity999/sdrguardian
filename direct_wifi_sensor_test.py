#!/usr/bin/env python3
import subprocess
import re
import asyncio
import time

class SimplifiedWifiSensor:
    """A simplified WiFi sensor that focuses only on parsing system_profiler output"""
    
    def __init__(self):
        self.interface = "en0"  # Default macOS WiFi interface
    
    async def scan_wifi(self):
        """Scan for WiFi networks and return the results"""
        networks = []
        success = False
        error_msg = None
        
        try:
            print("Running system_profiler SPAirPortDataType...")
            result = subprocess.run(
                ["system_profiler", "SPAirPortDataType"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = f"Error running system_profiler: {result.stderr}"
                return False, error_msg, []
            
            output = result.stdout
            print(f"Output length: {len(output)} characters")
            
            # Use the approach validated by our parser test
            lines = output.splitlines()
            unique_networks = set()  # Use a set to track unique network names
            
            # First check for current network
            in_current_section = False
            for i, line in enumerate(lines):
                if "Current Network Information:" in line:
                    in_current_section = True
                    print("Found 'Current Network Information' section")
                    continue
                
                if in_current_section and line.startswith("            ") and line.strip().endswith(":"):
                    # Make sure this is a network name, not a property
                    if not any(prop in line for prop in ["Channel:", "Security:", "PHY Mode:", "Network Type:"]):
                        ssid = line.strip().rstrip(':')
                        print(f"Found current network: {ssid}")
                        
                        # Look for signal strength
                        rssi = -65  # Default
                        for j in range(i, min(i+10, len(lines))):
                            if "Signal / Noise:" in lines[j]:
                                signal_match = re.search(r"Signal / Noise:\s*(-\d+)\s*dBm", lines[j])
                                if signal_match:
                                    rssi = int(signal_match.group(1))
                                    break
                        
                        networks.append({
                            "ssid": ssid,
                            "rssi": rssi,
                            "connected": True
                        })
                        unique_networks.add(ssid)
                        print(f"Added current network: {ssid} (RSSI: {rssi} dBm)")
                        break
            
            # Now look for other networks
            in_other_networks = False
            for i, line in enumerate(lines):
                if "Other Local Wi-Fi Networks:" in line:
                    in_other_networks = True
                    print("Found 'Other Local Wi-Fi Networks' section")
                    continue
                
                if in_other_networks and line.startswith("            ") and line.strip().endswith(":"):
                    ssid = line.strip().rstrip(':')
                    
                    # Skip property lines and verify this is a network by checking for PHY Mode
                    if not any(prop in line for prop in ["Channel:", "Security:", "PHY Mode:", "Network Type:"]):
                        is_network = False
                        for j in range(1, 5):
                            if i + j < len(lines) and "PHY Mode:" in lines[i + j]:
                                is_network = True
                                break
                        
                        if is_network and ssid not in unique_networks:
                            # Look for signal strength
                            rssi = -75  # Default
                            for j in range(i, min(i+10, len(lines))):
                                if "Signal / Noise:" in lines[j]:
                                    signal_match = re.search(r"Signal / Noise:\s*(-\d+)\s*dBm", lines[j])
                                    if signal_match:
                                        rssi = int(signal_match.group(1))
                                        break
                            
                            networks.append({
                                "ssid": ssid,
                                "rssi": rssi,
                                "connected": False
                            })
                            unique_networks.add(ssid)
                            print(f"Added other network: {ssid} (RSSI: {rssi} dBm)")
            
            if networks:
                success = True
                print(f"\nFound {len(networks)} networks:")
                for i, network in enumerate(networks):
                    connected = "✓" if network.get("connected", False) else " "
                    print(f"  {i+1}. [{connected}] {network.get('ssid')} (RSSI: {network.get('rssi')} dBm)")
            else:
                error_msg = "No WiFi networks detected despite hardware being available"
                print(error_msg)
                
        except Exception as e:
            error_msg = f"WiFi scan error: {e}"
            print(f"Exception: {e}")
        
        return success, error_msg, networks

async def main():
    print("===== Direct WiFi Sensor Test =====")
    sensor = SimplifiedWifiSensor()
    success, error, networks = await sensor.scan_wifi()
    
    print("\n===== SCAN RESULTS =====")
    print(f"Scan success: {success}")
    if error:
        print(f"Error: {error}")
    
    print(f"Networks found: {len(networks)}")
    if networks:
        for i, network in enumerate(networks):
            connected = "✓" if network.get("connected", False) else " "
            print(f"  {i+1}. [{connected}] {network.get('ssid')} (RSSI: {network.get('rssi')} dBm)")
    else:
        print("  No networks found!")

if __name__ == "__main__":
    asyncio.run(main())
