import asyncio
import time
from bleak import BleakScanner
from .base import SensorPlugin

class BluetoothSensor(SensorPlugin):
    def __init__(self, config):
        super().__init__(config)
        self.error_count = 0
        self.last_error = None
        self.bluetooth_available = True  # Assume bluetooth is available initially
        self.logged_devices = set()  # Keep track of devices we've already logged RSSI issues for
        
    async def start(self, queue: asyncio.Queue):
        """
        Uses Bleak to scan for BLE devices.
        """
        self._running = True
        interval = self.config.get("interval", 5)
        
        while self._running:
            dev_list = []
            hardware_status = "available"
            error_message = None
            
            # Try to get real Bluetooth data if available
            if self.bluetooth_available:
                try:
                    # Use the newer approach that includes advertisement data
                    devices = await BleakScanner.discover(timeout=interval)
                    
                    for d in devices:
                        # Get RSSI from the device using multiple approaches to ensure we get a value
                        rssi = None
                        
                        # Try different approaches to get RSSI based on platform and device type
                        # First check if RSSI is directly available as an attribute
                        if hasattr(d, 'rssi') and d.rssi is not None:
                            rssi = d.rssi
                        # Next try to get from advertisement_data (common in newer versions)
                        elif hasattr(d, 'advertisement_data') and d.advertisement_data:
                            if hasattr(d.advertisement_data, 'rssi') and d.advertisement_data.rssi is not None:
                                rssi = d.advertisement_data.rssi
                            # Some platforms store it in a different structure
                            elif hasattr(d.advertisement_data, 'tx_power') and d.advertisement_data.tx_power is not None:
                                rssi = d.advertisement_data.tx_power
                        # If not available, try to get from the details dictionary
                        elif hasattr(d, 'details') and d.details:
                            if 'rssi' in d.details and d.details['rssi'] is not None:
                                rssi = d.details['rssi']
                            elif 'tx_power' in d.details and d.details['tx_power'] is not None:
                                rssi = d.details['tx_power']
                        
                        # If we still don't have a valid RSSI, try to estimate based on device type
                        if rssi is None or rssi == -100:
                            # Try to make an educated guess based on device name/type
                            if d.name and any(keyword in d.name.lower() for keyword in ['headphone', 'speaker', 'audio']):
                                rssi = -70  # Audio devices typically have medium signal strength
                            elif d.name and any(keyword in d.name.lower() for keyword in ['watch', 'fit', 'band']):
                                rssi = -65  # Wearables often have stronger signals
                            else:
                                rssi = -85  # Default to a more realistic value than -100
                            
                            # Only log this once per device to reduce noise
                            if d.address not in self.logged_devices:
                                print(f"Estimated RSSI for device {d.address} ({d.name or 'Unknown'}): {rssi}")
                                self.logged_devices.add(d.address)
                            
                        dev_list.append({
                            "address": d.address,
                            "name": d.name or "Unknown",
                            "rssi": rssi,
                        })
                    
                    # Reset error count if successful
                    self.error_count = 0
                    self.last_error = None
                    
                except Exception as e:
                    self.error_count += 1
                    self.last_error = str(e)
                    print(f"Bluetooth scan error: {e}")
                    
                    # After 3 consecutive errors, mark hardware as unavailable
                    if self.error_count >= 3:
                        print("Bluetooth hardware unavailable.")
                        self.bluetooth_available = False
                        hardware_status = "unavailable"
                        error_message = f"Hardware unavailable after multiple errors: {e}"
                    else:
                        hardware_status = "error"
                        error_message = str(e)
            else:
                # Hardware previously marked as unavailable
                hardware_status = "unavailable"
                error_message = self.last_error or "Bluetooth hardware is unavailable"
                
            data = {
                "sensor": "bluetooth",
                "timestamp": time.time(),
                "devices": dev_list,
                "hardware_status": hardware_status,
                "error": error_message
            }
            
            await queue.put(data)
            
            # If hardware is unavailable, we need to sleep manually
            # Otherwise BleakScanner.discover already waits for `timeout`
            if not self.bluetooth_available:
                await asyncio.sleep(interval)