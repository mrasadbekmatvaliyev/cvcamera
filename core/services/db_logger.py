import threading
import queue
import logging
from detector.models import VehicleLog

logger = logging.getLogger(__name__)


class AsyncLogger:
    """
    Thread-safe background worker for database logging.
    Prevents the CV loop from blocking on DB I/O.
    """

    def __init__(self):
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        while True:
            task = self.queue.get()
            if task is None:
                self.queue.task_done()
                break
            try:
                object_id, vehicle_type, direction, confidence = task
                VehicleLog.objects.create(
                    object_id=object_id,
                    vehicle_type=vehicle_type,
                    direction=direction,
                    confidence=confidence,
                )
            except Exception as e:
                logger.error("AsyncLogger DB write failed: %s", e)
            finally:
                # Always mark done — even on exception — to unblock queue.join()
                self.queue.task_done()

    def log_detection(self, object_id: int, vehicle_type: str, direction: str, confidence: float = 0.0):
        self.queue.put((object_id, vehicle_type, direction, confidence))

    def stop(self):
        self.queue.put(None)
        self.worker_thread.join()


db_logger = AsyncLogger()
