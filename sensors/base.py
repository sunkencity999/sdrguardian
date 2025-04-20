import abc
import asyncio

class SensorPlugin(abc.ABC):
    """
    Abstract base class for sensor plugins.
    """
    def __init__(self, config: dict):
        self.config = config
        self._running = False

    @abc.abstractmethod
    async def start(self, queue: asyncio.Queue):
        """
        Start emitting sensor data into the provided asyncio.Queue.
        Should run until self.stop() is called.
        """
        pass

    def stop(self):
        """
        Signal the sensor to stop.
        """
        self._running = False