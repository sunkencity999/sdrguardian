import asyncio
import time
from bleak import BleakScanner
from .base import SensorPlugin

class BluetoothSensor(SensorPlugin):
    async def start(self, queue: asyncio.Queue):
        """
        Uses Bleak to scan for BLE devices.
        """
        self._running = True
        interval = self.config.get("interval", 5)
        while self._running:
            try:
                devices = await BleakScanner.discover(timeout=interval)
                dev_list = []
                for d in devices:
                    dev_list.append({
                        "address": d.address,
                        "name": d.name,
                        "rssi": d.rssi,
                    })
            except Exception:
                dev_list = []
            data = {
                "sensor": "bluetooth",
                "timestamp": time.time(),
                "devices": dev_list,
            }
            await queue.put(data)
            # BleakScanner.discover already waits for `timeout`
            # loop will continue scanning until stopped