import asyncio
import subprocess
import re
import os
import shutil
import platform
import time
import json
from datetime import datetime

class WifiSensor:
    """WiFi sensor for detecting nearby networks"""
    
    def __init__(self):
        """Initialize the WiFi sensor"""
        self.last_scan_time = 0
        self.last_networks = []
        self.last_error = None
        self.last_success = False
        self.wifi_interface = None
        self.airport_cmd = None
        self.sudo_available = False
        
        # Detect OS and set appropriate commands
        self._detect_platform()
        
    def _detect_platform(self):
        """Detect the operating system and set appropriate commands"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # Find the WiFi interface
            try:
                # Get the list of network interfaces
                result = subprocess.run(
                    ["networksetup", "-listallhardwareports"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Find the Wi-Fi interface
                wifi_interface = None
                for line in result.stdout.splitlines():
                    if "Wi-Fi" in line or "AirPort" in line:
                        # The next line should contain the interface name
                        for next_line in result.stdout.splitlines()[result.stdout.splitlines().index(line)+1:]:
                            if "Device:" in next_line:
                                match = re.search(r"Device:\s*([^\s]+)", next_line)
                                if match:
                                    wifi_interface = match.group(1)
                                    break
                        if wifi_interface:
                            break
                
                if not wifi_interface:
                    # Try another approach - look for en0 or similar
                    for line in result.stdout.splitlines():
                        if "Device: en" in line:
                            match = re.search(r"Device:\s*([^\s]+)", line)
                            if match:
                                wifi_interface = match.group(1)
                                break
                
                self.wifi_interface = wifi_interface or "en0"  # Default to en0 if not found
                print(f"Found Wi-Fi interface: {self.wifi_interface}")
                
                # Use modern tools for WiFi scanning
                if shutil.which("wdutil"):
                    self.airport_cmd = ["wdutil"]
                    print("Using wdutil for WiFi scanning (recommended)")
                elif shutil.which("system_profiler"):
                    self.airport_cmd = ["system_profiler"]
                    print("Using system_profiler for WiFi scanning (recommended)")
                else:
                    self.airport_cmd = ["networksetup"]
                    print("Using networksetup for WiFi scanning (limited)")
                    
                # Check if sudo is available without password
                try:
                    sudo_test = subprocess.run(
                        ["sudo", "-n", "echo", "test"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=1
                    )
                    self.sudo_available = sudo_test.returncode == 0
                except:
                    self.sudo_available = False
                    
                print(f"Hardware status: available")
                print(f"WiFi interface: {self.wifi_interface}")
                print(f"Airport command: {self.airport_cmd}")
                print(f"Sudo available: {self.sudo_available}")
                
            except Exception as e:
                print(f"Error detecting WiFi hardware: {e}")
                self.wifi_interface = "en0"  # Default
                self.airport_cmd = ["networksetup"]
                
        elif system == "Linux":
            # Linux implementation would go here
            self.wifi_interface = "wlan0"  # Default
            self.airport_cmd = ["iwlist"]
            
        elif system == "Windows":
            # Windows implementation would go here
            self.wifi_interface = "Wi-Fi"
            self.airport_cmd = ["netsh", "wlan", "show", "networks"]
            
        else:
            print(f"Unsupported platform: {system}")
            self.wifi_interface = "unknown"
            self.airport_cmd = None
            
    async def _scan_mac_wifi(self):
        """Scan for WiFi networks on macOS"""
        networks = []
        error_msg = None
        success = False
        
        if not self.airport_cmd:
            return False, "WiFi scanning tools not available", []
        
        # First, check if WiFi is enabled
        try:
            power_result = subprocess.run(
                ["networksetup", "-getairportpower", self.wifi_interface],
                capture_output=True,
                text=True,
                check=False,
                timeout=2
            )
            print(f"WiFi power status: {power_result.stdout}")
            
            if "Off" in power_result.stdout:
                return False, "WiFi is turned off", []
        except Exception as e:
            print(f"Error checking WiFi power: {e}")
            # Continue anyway, we'll try other methods
        
        # Try to get the current connected network first
        current_network = None
        try:
            # Get current network using networksetup
            current_result = subprocess.run(
                ["networksetup", "-getairportnetwork", self.wifi_interface],
                capture_output=True,
                text=True,
                check=False,
                timeout=2
            )
            
            print(f"Current network info:\n{current_result.stdout}")
            
            # Parse networksetup output which is typically: "Current Wi-Fi Network: SSID_NAME"
            ssid_match = re.search(r"Current Wi-Fi Network:\s*([^\n]+)", current_result.stdout)
            if ssid_match:
                current_network = ssid_match.group(1).strip()
                print(f"Currently connected to: {current_network}")
                
                # Add the current network to our list with estimated signal strength
                networks.append({
                    "ssid": current_network,
                    "rssi": -65,  # Moderate signal strength (estimated)
                    "connected": True
                })
                print(f"Added current network to list: {current_network}")
        except Exception as e:
            print(f"Error getting current network: {e}")
        
        # Try wdutil first if available (recommended modern approach)
        if self.airport_cmd and self.airport_cmd[0] == "wdutil":
            print("Scanning for available WiFi networks using wdutil info...")
            try:
                # wdutil requires sudo privileges
                if self.sudo_available:
                    # Use wdutil info command with sudo
                    scan_result = await self._run_with_sudo(
                        ["wdutil", "info"],
                        timeout=5
                    )
                else:
                    print("WARNING: wdutil requires sudo privileges. Falling back to other methods.")
                    scan_result = subprocess.run(
                        ["wdutil", "info"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5
                    )
                
                # Check if we got any output
                if scan_result.stdout.strip():
                    print(f"wdutil info output (truncated):\n{scan_result.stdout[:300]}...")
                    
                    # Parse the wdutil output to find networks
                    scan_section = False
                    for line in scan_result.stdout.splitlines():
                        # Look for current network
                        if "SSID:" in line and not scan_section:
                            ssid_match = re.search(r"SSID:\s*([^\n]+)", line)
                            if ssid_match and not any(n.get("ssid") == ssid_match.group(1).strip() for n in networks):
                                current_ssid = ssid_match.group(1).strip()
                                print(f"Found current network: {current_ssid}")
                                networks.append({
                                    "ssid": current_ssid,
                                    "rssi": -65,  # Estimated moderate signal
                                    "connected": True
                                })
                        
                        # Look for scan results section
                        if "Scan Results:" in line:
                            scan_section = True
                            continue
                            
                        if scan_section and line.strip() and ":" in line:
                            # Parse network info
                            parts = line.strip().split(":")
                            if len(parts) >= 2:
                                ssid = parts[0].strip()
                                details = parts[1].strip()
                                
                                # Extract RSSI if available
                                rssi_match = re.search(r"RSSI=(-?\d+)", details)
                                rssi = int(rssi_match.group(1)) if rssi_match else -75
                                
                                # Extract channel if available
                                channel_match = re.search(r"channel=(\d+)", details)
                                channel = channel_match.group(1) if channel_match else None
                                
                                # Create network info
                                network_info = {"ssid": ssid, "rssi": rssi}
                                
                                if channel:
                                    network_info["channel"] = channel
                                    
                                # Mark as connected if this is the current network
                                if current_network and ssid == current_network:
                                    network_info["connected"] = True
                                
                                # Only add if not already in the list
                                if not any(n.get("ssid") == ssid for n in networks):
                                    networks.append(network_info)
                                    print(f"Found WiFi network: {ssid} (RSSI: {rssi} dBm)")
                    
                    # If we found networks, return them
                    if networks:
                        return True, None, networks
                        
                    # If wdutil didn't find networks, try a different approach with wdutil
                    try:
                        # Try the Wi-Fi scan command with sudo if available
                        if self.sudo_available:
                            scan_cmd_result = await self._run_with_sudo(
                                ["wdutil", "scan"],
                                timeout=5
                            )
                        else:
                            print("WARNING: wdutil scan requires sudo privileges. Falling back to other methods.")
                            scan_cmd_result = subprocess.run(
                                ["wdutil", "scan"],
                                capture_output=True,
                                text=True,
                                check=False,
                                timeout=5
                            )
                        print(f"wdutil scan output:\n{scan_cmd_result.stdout}")
                        
                        # Wait a moment for scan to complete
                        await asyncio.sleep(2)
                        
                        # Get updated info with sudo if available
                        if self.sudo_available:
                            info_result = await self._run_with_sudo(
                                ["wdutil", "info"],
                                timeout=5
                            )
                        else:
                            info_result = subprocess.run(
                                ["wdutil", "info"],
                                capture_output=True,
                                text=True,
                                check=False,
                                timeout=5
                            )
                        
                        # Parse the scan results
                        scan_section = False
                        for line in info_result.stdout.splitlines():
                            if "Scan Results:" in line:
                                scan_section = True
                                continue
                                
                            if scan_section and line.strip() and ":" in line:
                                # Parse network info
                                parts = line.strip().split(":")
                                if len(parts) >= 2:
                                    ssid = parts[0].strip()
                                    details = parts[1].strip()
                                    
                                    # Extract RSSI if available
                                    rssi_match = re.search(r"RSSI=(-?\d+)", details)
                                    rssi = int(rssi_match.group(1)) if rssi_match else -75
                                    
                                    # Create network info
                                    network_info = {"ssid": ssid, "rssi": rssi}
                                    
                                    # Only add if not already in the list
                                    if not any(n.get("ssid") == ssid for n in networks):
                                        networks.append(network_info)
                                        print(f"Found WiFi network: {ssid} (RSSI: {rssi} dBm)")
                        
                        if networks:
                            return True, None, networks
                    except Exception as e:
                        print(f"Error with wdutil scan: {e}")
            except Exception as e:
                print(f"Error scanning with wdutil: {e}")
                # Continue to other methods if this fails
        
        # Try system_profiler as a fallback
        if not networks and shutil.which("system_profiler"):
            print("Scanning for available WiFi networks using system_profiler...")
            try:
                # Use system_profiler to get WiFi information
                scan_result = subprocess.run(
                    ["system_profiler", "SPAirPortDataType"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5
                )
                
                print(f"System profiler output (truncated):\n{scan_result.stdout[:300]}...")
                
                # Parse system_profiler output
                in_wifi_section = False
                in_networks_section = False
                current_network_info = {}
                network_info = {}
                
                for line in scan_result.stdout.splitlines():
                    line = line.strip()
                    
                    # Check for Wi-Fi section
                    if "Wi-Fi" in line and not in_wifi_section:
                        in_wifi_section = True
                        continue
                        
                    if not in_wifi_section:
                        continue
                        
                    # Check for current network
                    if "Current Network Information" in line:
                        in_networks_section = True
                        continue
                        
                    # Check for other visible networks
                    if "Other Networks Information" in line:
                        # Save current network if we have one
                        if current_network and current_network_info:
                            current_network_info["connected"] = True
                            if not any(n.get("ssid") == current_network for n in networks):
                                networks.append(current_network_info)
                                print(f"Found connected WiFi network: {current_network}")
                        
                        current_network_info = {}
                        continue
                        
                    # Parse network information
                    if in_networks_section and ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "SSID":
                            # If we were processing a network, add it to the list
                            if network_info and "ssid" in network_info:
                                if not any(n.get("ssid") == network_info["ssid"] for n in networks):
                                    networks.append(network_info)
                                    print(f"Found WiFi network: {network_info['ssid']}")
                            
                            # Start a new network
                            network_info = {"ssid": value}
                            
                            # If this is the first network and we're in the Current Network section
                            if "Current Network Information" in scan_result.stdout and not current_network_info:
                                current_network = value
                                current_network_info = network_info
                        elif key == "Signal Strength" and "ssid" in network_info:
                            # Convert signal strength to RSSI (approximate)
                            if "High" in value:
                                network_info["rssi"] = -50
                            elif "Medium" in value:
                                network_info["rssi"] = -70
                            else:
                                network_info["rssi"] = -85
                        elif key == "Channel" and "ssid" in network_info:
                            network_info["channel"] = value
                        elif key == "Security" and "ssid" in network_info:
                            network_info["security"] = value
                
                # Add the last network if we have one
                if network_info and "ssid" in network_info and not any(n.get("ssid") == network_info["ssid"] for n in networks):
                    networks.append(network_info)
                    print(f"Found WiFi network: {network_info['ssid']}")
                
                if networks:
                    return True, None, networks
            except Exception as e:
                print(f"Error scanning with system_profiler: {e}")
                # Continue to other methods if this fails
        
        # If we still have no networks, this is a critical error for a military application
        if not networks:
            # Check if the issue might be related to permissions
            if self.airport_cmd and self.airport_cmd[0] == "wdutil" and not self.sudo_available:
                error_msg = "CRITICAL: WiFi scanning requires sudo privileges for wdutil. Please run the application with sudo or provide sudo password."
            else:
                error_msg = "CRITICAL: WiFi hardware is active but no networks detected. This may indicate scanning permission issues, hardware malfunction, or signal jamming."
            print(error_msg)
            # For a military application, this is a serious issue that needs attention
            return False, error_msg, []
        
        return success, error_msg, networks
        
    async def _scan_linux_wifi(self):
        """Scan for WiFi networks on Linux"""
        # Not implemented yet
        return False, "Linux WiFi scanning not implemented", []
    
    async def _scan_windows_wifi(self):
        """Scan for WiFi networks on Windows"""
        # Not implemented yet
        return False, "Windows WiFi scanning not implemented", []
    
    async def _run_with_sudo(self, cmd, timeout=5):
        """Run a command with sudo if available"""
        if self.sudo_available:
            sudo_cmd = ["sudo", "-n"] + cmd
            try:
                result = subprocess.run(
                    sudo_cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout
                )
                return result
            except Exception as e:
                print(f"Error running command with sudo: {e}")
                # Fall back to non-sudo
                pass
        
        # Run without sudo
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout
            )
            return result
        except Exception as e:
            print(f"Error running command: {e}")
            return None
            
    async def scan(self):
        """Scan for WiFi networks"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            success, error_msg, networks = await self._scan_mac_wifi()
        elif system == "Linux":
            success, error_msg, networks = await self._scan_linux_wifi()
        elif system == "Windows":
            success, error_msg, networks = await self._scan_windows_wifi()
        else:
            success = False
            error_msg = f"Unsupported platform: {system}"
            networks = []
        
        # Update last scan results
        self.last_scan_time = time.time()
        self.last_networks = networks
        self.last_success = success
        self.last_error = error_msg
        
        return success, error_msg, networks
    
    def get_record(self):
        """Get a record of the current WiFi status"""
        # If we haven't scanned yet, return empty record
        if self.last_scan_time == 0:
            return {
                "sensor": "wifi",
                "timestamp": time.time(),
                "hardware_status": "unknown",
                "networks": []
            }
        
        # Determine hardware status
        if not self.airport_cmd:
            hardware_status = "unsupported"
        elif not self.last_success and self.last_error and "turned off" in self.last_error.lower():
            hardware_status = "off"
        elif not self.last_success:
            hardware_status = "error"
        else:
            hardware_status = "available"
        
        # Create record
        record = {
            "sensor": "wifi",
            "timestamp": time.time(),
            "hardware_status": hardware_status,
            "networks": self.last_networks
        }
        
        # Add error message if there was one
        if self.last_error:
            record["error"] = self.last_error
            
        return record
