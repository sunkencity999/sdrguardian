import asyncio
import time
import sys
import subprocess
import os
import shutil
from .base import SensorPlugin

class WifiSensor(SensorPlugin):
    async def start(self, queue: asyncio.Queue):
        self._running = True
        interval = self.config.get("interval", 5)
        is_linux = sys.platform.startswith("linux")
        is_mac = sys.platform == "darwin"
        # Determine airport command on Mac
        airport_cmd = None
        if is_mac:
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            if os.path.exists(airport_path):
                airport_cmd = [airport_path]
            elif shutil.which("airport"):
                airport_cmd = ["airport"]
        while self._running:
            networks = []
            if is_linux:
                try:
                    result = subprocess.run(
                        ["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi", "list"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    for line in result.stdout.splitlines():
                        if not line:
                            continue
                        parts = line.split(":", 1)
                        if len(parts) != 2:
                            continue
                        ssid, signal = parts
                        ssid = ssid.strip()
                        try:
                            rssi = int(signal.strip())
                        except ValueError:
                            continue
                        networks.append({"ssid": ssid, "rssi": rssi})
                except Exception:
                    pass
            elif is_mac and airport_cmd:
                try:
                    result = subprocess.run(
                        airport_cmd + ["-s"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    lines = result.stdout.splitlines()
                    # Skip header and parse fixed-width columns: SSID [0:32], RSSI [49:55]
                    if len(lines) >= 2:
                        for line in lines[1:]:
                            if len(line) < 55:
                                continue
                            ssid = line[0:32].strip()
                            rssi_str = line[49:55].strip()
                            try:
                                rssi = int(rssi_str)
                            except ValueError:
                                continue
                            networks.append({"ssid": ssid, "rssi": rssi})
                except Exception:
                    pass
            data = {
                "sensor": "wifi",
                "timestamp": time.time(),
                "networks": networks,
            }
            await queue.put(data)
            await asyncio.sleep(interval)