import asyncio
import time
import subprocess
import sys
import re
from .base import SensorPlugin

class ImuSensor(SensorPlugin):
    def __init__(self, config):
        super().__init__(config)
        self.is_mac = sys.platform == "darwin"
        self.is_linux = sys.platform.startswith("linux")
        self.error_count = 0
        self.last_error = None
        
        # Check for available sensors
        self.has_smc = self._check_smc_available() if self.is_mac else False
        self.has_motion = self._check_motion_sensors_available() if self.is_mac else False
        
        # Initial hardware status
        if self.is_mac and not self.has_motion:
            self.hardware_status = "unavailable"
            self.last_error = "No motion sensors detected on this Mac"
        elif self.is_linux and not self._check_linux_sensors_available():
            self.hardware_status = "unavailable"
            self.last_error = "No motion sensors detected on this Linux system"
        elif not (self.is_mac or self.is_linux):
            self.hardware_status = "unsupported"
            self.last_error = f"Unsupported platform: {sys.platform}"
        else:
            self.hardware_status = "available"
        
    def _check_smc_available(self):
        """Check if SMC (System Management Controller) is available on Mac"""
        try:
            result = subprocess.run(["which", "smckit"], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_motion_sensors_available(self):
        """Check if motion sensors are available on Mac"""
        try:
            # Try to use the Mac's built-in motion sensors via ioreg
            result = subprocess.run(
                ["ioreg", "-r", "-c", "SMCMotionSensor"], 
                capture_output=True, 
                text=True
            )
            return "SMCMotionSensor" in result.stdout
        except Exception:
            return False
    
    def _check_linux_sensors_available(self):
        """Check if motion sensors are available on Linux"""
        try:
            result = subprocess.run(
                ["find", "/sys/bus/iio/devices", "-name", "*accel*"],
                capture_output=True,
                text=True,
                timeout=1
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def _get_mac_motion_data(self):
        """Get motion sensor data from Mac's built-in sensors"""
        accel = {"x": 0.0, "y": 0.0, "z": 0.0}
        gyro = {"x": 0.0, "y": 0.0, "z": 0.0}
        mag = {"x": 0.0, "y": 0.0, "z": 0.0}
        success = False
        error_msg = None
        
        try:
            # Try to get accelerometer data
            if self.has_motion:
                result = subprocess.run(
                    ["ioreg", "-r", "-c", "SMCMotionSensor", "-w0"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                
                # Parse x, y, z acceleration values
                x_match = re.search(r'"x" = ([\-0-9.]+)', result.stdout)
                y_match = re.search(r'"y" = ([\-0-9.]+)', result.stdout)
                z_match = re.search(r'"z" = ([\-0-9.]+)', result.stdout)
                
                if x_match and y_match and z_match:
                    accel["x"] = float(x_match.group(1))
                    accel["y"] = float(y_match.group(1))
                    accel["z"] = float(z_match.group(1))
                    success = True
                else:
                    error_msg = "Could not parse motion sensor data"
            else:
                error_msg = "No motion sensors available on this Mac"
            
            # Try to get orientation data using system_profiler
            if success:
                try:
                    orientation_result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType"],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    
                    # Look for orientation information that might indicate device position
                    if "Orientation" in orientation_result.stdout:
                        orientation_match = re.search(r'Orientation: (\w+)', orientation_result.stdout)
                        if orientation_match:
                            orientation = orientation_match.group(1)
                            # Adjust gyro based on orientation
                            if orientation == "Rotated":
                                gyro["z"] = 1.0  # Indicate rotation
                except Exception as e:
                    # Non-critical error, just log it
                    print(f"Error getting orientation data: {e}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error reading motion sensors: {e}")
        
        return success, error_msg, accel, gyro, mag
    
    def _get_linux_motion_data(self):
        """Get motion sensor data from Linux sensors"""
        accel = {"x": 0.0, "y": 0.0, "z": 0.0}
        gyro = {"x": 0.0, "y": 0.0, "z": 0.0}
        mag = {"x": 0.0, "y": 0.0, "z": 0.0}
        success = False
        error_msg = None
        
        try:
            # Try to read from IIO sensors (common on Linux laptops)
            result = subprocess.run(
                ["find", "/sys/bus/iio/devices", "-name", "*accel*"],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            accel_paths = result.stdout.strip().split('\n')
            if accel_paths and accel_paths[0]:
                # Found accelerometer, try to read values
                values_read = 0
                for axis in ['x', 'y', 'z']:
                    try:
                        with open(f"{accel_paths[0]}/in_accel_{axis}_raw", 'r') as f:
                            value = float(f.read().strip())
                            # Convert raw value to m/s^2 (device-specific scaling would be needed)
                            accel[axis] = value / 1000.0  # Example scaling
                            values_read += 1
                    except Exception:
                        pass
                
                success = values_read > 0
                if not success:
                    error_msg = "Could not read values from accelerometer"
            else:
                error_msg = "No accelerometer found in IIO devices"
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error reading Linux motion sensors: {e}")
        
        return success, error_msg, accel, gyro, mag
    
    async def start(self, queue: asyncio.Queue):
        self._running = True
        interval = self.config.get("interval", 1)
        
        while self._running:
            success = False
            error_msg = None
            accel = {"x": 0.0, "y": 0.0, "z": 0.0}
            gyro = {"x": 0.0, "y": 0.0, "z": 0.0}
            mag = {"x": 0.0, "y": 0.0, "z": 0.0}
            
            # Only try to get data if hardware is available
            if self.hardware_status == "available":
                # Get actual hardware sensor data based on platform
                if self.is_mac:
                    success, error_msg, accel, gyro, mag = self._get_mac_motion_data()
                elif self.is_linux:
                    success, error_msg, accel, gyro, mag = self._get_linux_motion_data()
                else:
                    success = False
                    error_msg = f"Unsupported platform: {sys.platform}"
                
                # Update hardware status based on success/failure
                if not success:
                    self.error_count += 1
                    self.last_error = error_msg
                    
                    if self.error_count >= 3:
                        print(f"IMU hardware unavailable: {error_msg}")
                        self.hardware_status = "unavailable"
                    else:
                        self.hardware_status = "error"
                else:
                    self.error_count = 0
                    self.hardware_status = "available"
                    self.last_error = None
            else:
                # Hardware already marked as unavailable
                success = False
                error_msg = self.last_error
            
            # Create sensor data record
            data = {
                "sensor": "imu",
                "timestamp": time.time(),
                "accel": accel,
                "gyro": gyro,
                "mag": mag,
                "hardware_status": self.hardware_status,
                "error": error_msg
            }
            
            await queue.put(data)
            await asyncio.sleep(interval)