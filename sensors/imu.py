import asyncio
import time
from .base import SensorPlugin

class ImuSensor(SensorPlugin):
    async def start(self, queue: asyncio.Queue):
        self._running = True
        interval = self.config.get("interval", 1)
        while self._running:
            # TODO: implement real IMU data reading
            data = {
                "sensor": "imu",
                "timestamp": time.time(),
                "accel": {"x": 0, "y": 0, "z": 0},
                "gyro": {"x": 0, "y": 0, "z": 0},
                "mag": {"x": 0, "y": 0, "z": 0}
            }
            await queue.put(data)
            await asyncio.sleep(interval)