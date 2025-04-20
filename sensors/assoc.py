import asyncio
import time
import sys
import subprocess
import os
import shutil
from .base import SensorPlugin

class AssocSensor(SensorPlugin):
    """
    Sensor plugin to monitor current Wi-Fi SSID association.
    Emits records with 'ssid' field.
    """
    async def start(self, queue: asyncio.Queue):
        self._running = True
        interval = self.config.get("interval", 5)
        is_linux = sys.platform.startswith("linux")
        is_mac = sys.platform == "darwin"
        # Determine airport command on Mac
        airport_cmd = None
        if is_mac:
            path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            if os.path.exists(path):
                airport_cmd = [path]
            elif shutil.which("airport"):
                airport_cmd = ["airport"]
        prev_ssid = None
        while self._running:
            ssid = None
            if is_linux:
                try:
                    result = subprocess.run(
                        ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                        capture_output=True, text=True, check=False
                    )
                    for line in result.stdout.splitlines():
                        parts = line.split(":", 1)
                        if len(parts) == 2 and parts[0] == "yes":
                            ssid = parts[1]
                            break
                except Exception:
                    pass
            elif is_mac and airport_cmd:
                try:
                    res = subprocess.run(
                        airport_cmd + ["-I"], capture_output=True, text=True, check=False
                    )
                    for line in res.stdout.splitlines():
                        if line.strip().startswith("SSID:"):
                            ssid = line.split("SSID:", 1)[1].strip()
                            break
                except Exception:
                    pass
            record = {"sensor": "assoc", "timestamp": time.time(), "ssid": ssid}
            await queue.put(record)
            await asyncio.sleep(interval)