import asyncio
import time
import psutil
from .base import SensorPlugin

class NetIOSensor(SensorPlugin):
    """
    Sensor plugin to monitor network I/O and compute per-second rates.
    """
    async def start(self, queue: asyncio.Queue):
        self._running = True
        interval = self.config.get("interval", 5)
        prev = psutil.net_io_counters()
        while self._running:
            await asyncio.sleep(interval)
            current = psutil.net_io_counters()
            sent_delta = current.bytes_sent - prev.bytes_sent
            recv_delta = current.bytes_recv - prev.bytes_recv
            rate_sent = sent_delta / interval
            rate_recv = recv_delta / interval
            record = {
                "sensor": "netio",
                "timestamp": time.time(),
                "rate_sent": rate_sent,
                "rate_recv": rate_recv,
            }
            await queue.put(record)
            prev = current