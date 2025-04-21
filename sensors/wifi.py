import asyncio
import subprocess
import re
import os
import shutil
import platform
import time
import json
import sys
from datetime import datetime
from .base import SensorPlugin

class WifiSensor(SensorPlugin):
    """WiFi sensor for detecting nearby networks"""
    
    def __init__(self, config):
        """Initialize the WiFi sensor"""
        super().__init__(config)
        self.last_scan_time = 0
        self.last_networks = []
        self.last_error = None
        self.last_success = False
        self.wifi_interface = None
        self.scan_cmd = None
        self.sudo_available = False
        self.is_mac = sys.platform == "darwin"
        self.is_linux = sys.platform.startswith("linux")
        self.hardware_status = "unknown"
        
        # Get sudo password from config or environment variable
        self.sudo_password = config.get("sudo_password", None)
        if not self.sudo_password and "SUDO_PASSWORD" in os.environ:
            self.sudo_password = os.environ.get("SUDO_PASSWORD")
            print("Using sudo password from environment variable")
        
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
                        match = re.search(r"Device:\s*([^\s]+)", next(iter([l for l in result.stdout.splitlines() if "Device:" in l and result.stdout.splitlines().index(l) > result.stdout.splitlines().index(line)]), ""))
                        if match:
                            wifi_interface = match.group(1)
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
                    self.scan_cmd = ["wdutil"]
                    print("Using wdutil for WiFi scanning (recommended)")
                    # Check if sudo is available
                    if self.sudo_password:
                        self.sudo_available = True
                        print("Sudo password available for wdutil")
                    else:
                        # Try passwordless sudo
                        try:
                            sudo_test = subprocess.run(
                                ["sudo", "-n", "echo", "test"],
                                capture_output=True,
                                text=True,
                                check=False,
                                timeout=1
                            )
                            self.sudo_available = sudo_test.returncode == 0
                            if self.sudo_available:
                                print("Passwordless sudo available for wdutil")
                            else:
                                print("WARNING: wdutil requires sudo privileges, which are not available")
                        except Exception:
                            self.sudo_available = False
                elif shutil.which("system_profiler"):
                    self.scan_cmd = ["system_profiler"]
                    print("Using system_profiler for WiFi scanning (recommended)")
                else:
                    self.scan_cmd = ["networksetup"]
                    print("Using networksetup for WiFi scanning (limited)")
                
                self.hardware_status = "available"
                    
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
                print(f"Scan command: {self.scan_cmd}")
                print(f"Sudo available: {self.sudo_available}")
                
            except Exception as e:
                print(f"Error detecting WiFi hardware: {e}")
                self.wifi_interface = "en0"  # Default
                self.scan_cmd = ["networksetup"]
                
        elif system == "Linux":
            # Linux implementation would go here
            self.wifi_interface = "wlan0"  # Default
            self.scan_cmd = ["iwlist"]
            
        elif system == "Windows":
            # Windows implementation would go here
            self.wifi_interface = "Wi-Fi"
            self.scan_cmd = ["netsh", "wlan", "show", "networks"]
            
        else:
            print(f"Unsupported platform: {system}")
            self.wifi_interface = "unknown"
            self.scan_cmd = None
            
    async def _scan_mac_wifi(self):
        """Scan for WiFi networks on macOS"""
        networks = []
        error_msg = None
        success = False
        
        if not self.scan_cmd:
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
        
        try:
            # Try wdutil first if available (requires sudo)
            if self.scan_cmd[0] == "wdutil":
                print("Scanning for available WiFi networks using wdutil...")
                
                # Try to run wdutil with sudo if needed
                if self.sudo_available or self.sudo_password:
                    scan_result = self._run_with_sudo(
                        ["wdutil", "info"],
                        timeout=5
                    )
                else:
                    # Try without sudo (will likely fail)
                    scan_result = subprocess.run(
                        ["wdutil", "info"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5
                    )
                
                # Parse the wdutil output to find networks
                if scan_result and scan_result.stdout:
                    print(f"wdutil info output (truncated):\n{scan_result.stdout[:300]}...")
                    
                    # Look for current connected network
                    current_ssid = None
                    
                    # Try to find the current network in the wdutil output
                    for line in scan_result.stdout.splitlines():
                        if "SSID:" in line:
                            ssid_match = re.search(r"SSID:\s*([^\n]+)", line)
                            if ssid_match:
                                current_ssid = ssid_match.group(1).strip()
                                if current_ssid and not any(n.get("ssid") == current_ssid for n in networks):
                                    print(f"Found current network: {current_ssid}")
                                    networks.append({
                                        "ssid": current_ssid,
                                        "rssi": -65,  # Estimated moderate signal
                                        "connected": True
                                    })
                                    break
                    
                    # Try to run a scan with wdutil scan
                    print("Running wdutil scan to find available networks...")
                    try:
                        scan_cmd_result = self._run_with_sudo(
                            ["wdutil", "scan"],
                            timeout=5
                        )
                        print(f"wdutil scan result: {scan_cmd_result.returncode}")
                        
                        # Wait a moment for scan to complete
                        await asyncio.sleep(2)
                        
                        # Get updated info after scan
                        info_result = self._run_with_sudo(
                            ["wdutil", "info"],
                            timeout=5
                        )
                        
                        if info_result and info_result.stdout:
                            # Look for networks section
                            in_networks_section = False
                            for line in info_result.stdout.splitlines():
                                # Look for networks section
                                if "Networks In Range:" in line or "Scan Results:" in line:
                                    in_networks_section = True
                                    continue
                                
                                # Parse network entries in the networks section
                                if in_networks_section and ":" in line and not line.startswith(" "):
                                    parts = line.split(":")
                                    if len(parts) >= 2:
                                        ssid = parts[0].strip()
                                        details = parts[1].strip()
                                        
                                        # Skip if empty SSID
                                        if not ssid:
                                            continue
                                        
                                        # Create network info
                                        network_info = {"ssid": ssid, "rssi": -75}  # Default signal strength
                                        
                                        # Mark as connected if this is the current network
                                        if current_ssid and ssid == current_ssid:
                                            network_info["connected"] = True
                                        
                                        # Only add if not already in the list
                                        if not any(n.get("ssid") == ssid for n in networks):
                                            networks.append(network_info)
                                            print(f"Found WiFi network: {ssid}")
                    except Exception as e:
                        print(f"Error with wdutil scan: {e}")
            
            # Try system_profiler as a fallback
            elif self.scan_cmd[0] == "system_profiler":
                print("Scanning for available WiFi networks using system_profiler...")
                scan_result = subprocess.run(
                    ["system_profiler", "SPAirPortDataType"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5
                )
                
                # Parse the system_profiler output
                if scan_result and scan_result.stdout:
                    print(f"system_profiler output received, length: {len(scan_result.stdout)}")
                    print(f"system_profiler output (truncated):\n{scan_result.stdout[:300]}...")
                    
                    # Variables to track parsing state
                    current_network = None
                    in_wifi_section = False
                    in_current_network_section = False
                    in_other_networks_section = False
                    current_ssid = None
                    
                    for line in scan_result.stdout.splitlines():
                        line = line.strip()
                        
                        # Look for Wi-Fi section
                        if "Wi-Fi:" in line:
                            in_wifi_section = True
                            continue
                            
                        # Look for current network section
                        if in_wifi_section and "Current Network Information:" in line:
                            in_current_network_section = True
                            in_other_networks_section = False
                            continue
                            
                        # Look for other networks section
                        if in_wifi_section and "Other Local Wi-Fi Networks:" in line:
                            in_current_network_section = False
                            in_other_networks_section = True
                            continue
                            
                        # Get current network SSID
                        if in_current_network_section and line and ":" in line:
                            parts = line.split(":")
                            if len(parts) >= 1:
                                current_ssid = parts[0].strip()
                                if current_ssid and not any(n.get("ssid") == current_ssid for n in networks):
                                    # Add current network
                                    current_network = {
                                        "ssid": current_ssid,
                                        "rssi": -65,  # Default value until we find the actual signal strength
                                        "connected": True
                                    }
                                    print(f"Found current network: {current_ssid}")
                        
                        # Get signal strength for current network
                        if in_current_network_section and "Signal / Noise:" in line and current_network:
                            signal_match = re.search(r"Signal / Noise:\s*(-\d+)\s*dBm", line)
                            if signal_match:
                                current_network["rssi"] = int(signal_match.group(1))
                                networks.append(current_network)
                                print(f"Current network signal strength: {current_network['rssi']} dBm")
                                current_network = None
                        
                        # Parse other networks
                        if in_other_networks_section and line and not line.startswith(" ") and ":" in line:
                            parts = line.split(":")
                            if len(parts) >= 1:
                                ssid = parts[0].strip()
                                if ssid and not any(n.get("ssid") == ssid for n in networks):
                                    # Add other network
                                    network_info = {
                                        "ssid": ssid,
                                        "rssi": -75,  # Default value
                                        "connected": False
                                    }
                                    networks.append(network_info)
                                    print(f"Found other network: {ssid}")
                                    
                        # Get signal strength for other networks
                        if in_other_networks_section and "Signal / Noise:" in line and networks:
                            signal_match = re.search(r"Signal / Noise:\s*(-\d+)\s*dBm", line)
                            if signal_match and len(networks) > 0:
                                # Update the most recently added network
                                for network in reversed(networks):
                                    if not network.get("connected", False):
                                        network["rssi"] = int(signal_match.group(1))
                                        print(f"Updated signal strength for {network['ssid']}: {network['rssi']} dBm")
                                        break
            
            success = True
        except subprocess.TimeoutExpired:
            error_msg = "WiFi scan timed out"
        except Exception as e:
            error_msg = f"WiFi scan error: {e}"
        
        # If we still have no networks, try using more aggressive methods
        if not networks:
            print("No networks found with primary methods. Trying more aggressive scanning...")
            
            # Try using airport command directly if it exists (even though it's deprecated)
            # This is a last resort for military applications where getting real data is critical
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            if os.path.exists(airport_path):
                print("NOTICE: Using deprecated airport command as last resort to get critical network data")
                try:
                    # Try to scan with airport command
                    airport_result = subprocess.run(
                        [airport_path, "-s"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5
                    )
                    
                    # Parse the airport scan output
                    lines = airport_result.stdout.strip().split('\n')
                    header_skipped = False
                    
                    for line in lines:
                        # Skip the header line
                        if not header_skipped and "SSID" in line:
                            header_skipped = True
                            continue
                            
                        if line.strip() and not line.startswith("WARNING"):
                            # Split by whitespace but preserve SSIDs with spaces
                            parts = re.split(r'\s{2,}', line.strip())
                            if len(parts) >= 2:  # Need at least SSID and some other info
                                ssid = parts[0].strip()
                                if not ssid:
                                    continue  # Skip entries with empty SSIDs
                                
                                # Extract RSSI value
                                rssi = -75  # Default moderate-weak signal
                                for part in parts[1:]:
                                    if part.strip().startswith("-") and part.strip().replace("-", "").isdigit():
                                        rssi = int(part.strip())
                                        break
                                
                                # Create network info
                                network_info = {"ssid": ssid, "rssi": rssi}
                                
                                # Add channel if available
                                for i, part in enumerate(parts):
                                    if part.strip().isdigit() and i < len(parts)-1:
                                        if parts[i+1].strip().startswith("Y") or parts[i+1].strip().startswith("N"):
                                            network_info["channel"] = part.strip()
                                            break
                                
                                # Add security info if available
                                for part in parts:
                                    if any(security in part for security in ["WPA", "WEP", "NONE", "Open"]):
                                        network_info["security"] = part.strip()
                                        break
                                
                                networks.append(network_info)
                                print(f"Found WiFi network via airport: {ssid} (RSSI: {rssi} dBm)")
                    
                    if networks:
                        success = True
                        error_msg = None
                except Exception as e:
                    print(f"Error using airport command: {e}")
            
            # As a last resort, try to get at least the current network
            if not networks:
                try:
                    # Try to get the current network using networksetup
                    current_result = subprocess.run(
                        ["networksetup", "-getairportnetwork", self.wifi_interface],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=2
                    )
                    
                    print(f"Current network info from networksetup: {current_result.stdout}")
                    
                    # Parse networksetup output which is typically: "Current Wi-Fi Network: SSID_NAME"
                    ssid_match = re.search(r"Current Wi-Fi Network:\s*([^\n]+)", current_result.stdout)
                    if ssid_match:
                        current_network = ssid_match.group(1).strip()
                        print(f"Found current network via networksetup: {current_network}")
                        
                        # Add the current network to our list with estimated signal strength
                        networks.append({
                            "ssid": current_network,
                            "rssi": -65,  # Moderate signal strength (estimated)
                            "connected": True
                        })
                        success = True  # We found at least one network
                except Exception as e:
                    print(f"Error getting current network: {e}")
        

        
        # If we still have no networks, this is a critical error for a military application
        if not networks:
            # Check if the issue might be related to permissions
            if self.scan_cmd and self.scan_cmd[0] == "wdutil" and not self.sudo_available and not self.sudo_password:
                # Prompt for sudo password
                if self._prompt_for_sudo_password():
                    # Try scanning again with the newly provided password
                    print("Retrying WiFi scan with sudo privileges...")
                    return await self._scan_mac_wifi()
                else:
                    error_msg = "CRITICAL: WiFi scanning requires sudo privileges for wdutil. Please run the application with sudo or provide sudo password."
            else:
                # Collect diagnostic information to help determine why no networks are detected
                diagnostics = []
                
                # Check WiFi power status
                try:
                    power_result = subprocess.run(
                        ["networksetup", "-getairportpower", self.wifi_interface],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=2
                    )
                    diagnostics.append(f"WiFi Power: {power_result.stdout.strip()}")
                except Exception as e:
                    diagnostics.append(f"Error checking WiFi power: {e}")
                
                # Check if interface exists
                try:
                    ifconfig_result = subprocess.run(
                        ["ifconfig", self.wifi_interface],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=2
                    )
                    if ifconfig_result.returncode == 0:
                        diagnostics.append(f"Interface {self.wifi_interface} exists")
                    else:
                        diagnostics.append(f"Interface {self.wifi_interface} may not exist")
                except Exception as e:
                    diagnostics.append(f"Error checking interface: {e}")
                
                # Format diagnostic information
                diag_str = "\n  - " + "\n  - ".join(diagnostics)
                
                error_msg = f"CRITICAL: WiFi hardware is active but no networks detected. {diag_str}\n\nThis may indicate scanning permission issues, hardware malfunction, or signal jamming."
            
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
    
    def _prompt_for_sudo_password(self):
        """Prompt the user for sudo password if needed"""
        if self.sudo_password:
            return True
        
        # Check if passwordless sudo is available
        try:
            sudo_test = subprocess.run(
                ["sudo", "-n", "echo", "test"],
                capture_output=True,
                text=True,
                check=False,
                timeout=1
            )
            if sudo_test.returncode == 0:
                self.sudo_available = True
                print("Passwordless sudo is available")
                return True
        except Exception:
            pass
        
        # Prompt for password if passwordless sudo is not available
        try:
            # Use getpass to securely prompt for password
            import getpass
            print("\nWiFi scanning with wdutil requires sudo privileges.")
            self.sudo_password = getpass.getpass("Enter sudo password: ")
            return True if self.sudo_password else False
        except Exception as e:
            print(f"Error prompting for sudo password: {e}")
            return False
    
    def _run_with_sudo(self, cmd, timeout=5):
        """Run a command with sudo privileges"""
        try:
            if self.sudo_password:
                # Use the provided sudo password
                sudo_cmd = ["sudo", "-S"] + cmd
                process = subprocess.Popen(
                    sudo_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=f"{self.sudo_password}\n", timeout=timeout)
                return subprocess.CompletedProcess(
                    sudo_cmd, process.returncode, stdout=stdout, stderr=stderr
                )
            elif self.sudo_available:
                # Use passwordless sudo
                sudo_cmd = ["sudo", "-n"] + cmd
                return subprocess.run(
                    sudo_cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout
                )
            else:
                # No sudo available, run without sudo
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout
                )
        except Exception as e:
            print(f"Error running command: {e}")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=str(e))
            
    async def start(self, queue: asyncio.Queue):
        """Start the WiFi sensor"""
        self._running = True
        interval = self.config.get("interval", 5)
        sudo_prompt_shown = False
        
        while self._running:
            networks = []
            error_msg = None
            success = False
            
            # Check if we need sudo and don't have it yet
            if self.is_mac and self.scan_cmd and self.scan_cmd[0] == "wdutil" and not self.sudo_available and not self.sudo_password and not sudo_prompt_shown:
                # Prompt for sudo password
                sudo_prompt_shown = True
                if self._prompt_for_sudo_password():
                    print("Sudo password obtained. WiFi scanning will use elevated privileges.")
                else:
                    print("No sudo password provided. WiFi scanning may be limited.")
            
            # Only try to scan if hardware is available
            if self.hardware_status == "available":
                if self.is_mac:
                    success, error_msg, networks = await self._scan_mac_wifi()
                elif self.is_linux:
                    success, error_msg, networks = await self._scan_linux_wifi()
                elif self.is_windows:
                    success, error_msg, networks = await self._scan_windows_wifi()
                
                # Update hardware status based on success/failure
                if not success:
                    self.last_error = error_msg
                    if error_msg and "turned off" in error_msg.lower():
                        self.hardware_status = "off"
                    else:
                        self.hardware_status = "error"
                else:
                    self.hardware_status = "available"
                    self.last_error = None
            else:
                # Hardware already marked as unavailable
                error_msg = self.last_error
            
            # Create sensor data record
            data = {
                "sensor": "wifi",
                "timestamp": time.time(),
                "networks": networks,
                "hardware_status": self.hardware_status,
                "error": error_msg
            }
            
            # Update last scan results
            self.last_scan_time = time.time()
            self.last_networks = networks
            self.last_success = success
            self.last_error = error_msg
            
            await queue.put(data)
            await asyncio.sleep(interval)
    
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
        if not self.scan_cmd:
            hardware_status = "unsupported"
        elif not self.last_success and self.last_error and "turned off" in self.last_error.lower():
            hardware_status = "off"
        elif not self.last_success and self.last_error:
            hardware_status = "error"
        elif self.last_success and self.last_networks:
            hardware_status = "active"  # Successfully detected networks
        else:
            hardware_status = "available"  # Hardware available but no networks detected
        
        # Create record
        record = {
            "sensor": "wifi",
            "timestamp": time.time(),
            "hardware_status": hardware_status,
            "networks": self.last_networks,
            "scan_time": self.last_scan_time
        }
        
        # Add error message if there was one
        if self.last_error:
            record["error"] = self.last_error
            
        return record