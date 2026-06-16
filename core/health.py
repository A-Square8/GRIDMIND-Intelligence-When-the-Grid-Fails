import time
import shutil
import logging
import resource
from pathlib import Path

logger = logging.getLogger(__name__)


class SystemHealth:
    def __init__(self, llm_backend=None, store_dir="data/vector_store"):
        self.llm_backend = llm_backend
        self.store_dir = Path(store_dir)
        self.start_time = time.time()

    def get_report(self):
        return {
            "uptime_seconds": int(time.time() - self.start_time),
            "uptime_human": self._format_uptime(),
            "ram_mb": round(self._get_ram_mb(), 1),
            "disk_free_mb": self._get_disk_free(),
            "ollama_status": self._check_ollama(),
            "index_status": self._check_index(),
        }

    def _format_uptime(self):
        seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}h {minutes}m {secs}s"

    def _get_ram_mb(self):
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

    def _get_disk_free(self):
        try:
            usage = shutil.disk_usage(str(self.store_dir))
            return int(usage.free / (1024 * 1024))
        except Exception:
            return -1

    def _check_ollama(self):
        if self.llm_backend and hasattr(self.llm_backend, "health_check"):
            try:
                return self.llm_backend.health_check()
            except Exception:
                return False
        return "unknown"

    def _check_index(self):
        index_path = self.store_dir / "index.faiss"
        metadata_path = self.store_dir / "metadata.json"
        return index_path.exists() and metadata_path.exists()
