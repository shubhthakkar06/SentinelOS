from __future__ import annotations

"""
sentinel_os/monitoring/logger.py
----------------------------------
Structured logger with log levels and optional file output.
Replaces the original 5-line print wrapper.
"""

import logging
import sys
from collections import deque

class Logger:
    """
    Lightweight structured logger wrapping Python's stdlib logging.

    Supports:
      - Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
      - Circular buffer for shell 'audit' trail
      - Silenceable for benchmark runs (verbose=False)
    """

    def __init__(
        self,
        name: str = "SentinelOS",
        verbose: bool = True,
        log_file: str | None = None,
        level: int = logging.INFO,
    ):
        self.verbose = verbose
        self.history = deque(maxlen=100)  # Circular buffer for shell
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)

        self._logger.handlers.clear()

        self.fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                     datefmt="%H:%M:%S")

        self.stream_handler = None
        if verbose:
            self.stream_handler = logging.StreamHandler(sys.stdout)
            self.stream_handler.setLevel(level)
            self.stream_handler.setFormatter(self.fmt)
            self._logger.addHandler(self.stream_handler)

        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file, mode="a")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(self.fmt)
            self._logger.addHandler(fh)

    def mute(self):
        """Disable stdout printing."""
        if self.stream_handler:
            self._logger.removeHandler(self.stream_handler)

    def unmute(self):
        """Restore stdout printing."""
        if self.stream_handler:
            if self.stream_handler not in self._logger.handlers:
                self._logger.addHandler(self.stream_handler)

    def log(self, message: str, level: str = "INFO"):
        lvl = level.upper()
        # Add to history (always, even if muted)
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.history.append(f"{ts} [{lvl}] {message}")
        
        getattr(self._logger, lvl.lower(), self._logger.info)(message)

    def get_recent_logs(self, n=20):
        return list(self.history)[-n:]

    def debug(self, msg: str):   self.log(msg, "DEBUG")
    def info(self, msg: str):    self.log(msg, "INFO")
    def warning(self, msg: str): self.log(msg, "WARNING")
    def error(self, msg: str):   self.log(msg, "ERROR")