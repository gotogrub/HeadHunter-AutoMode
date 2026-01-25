"""
HeadHunter Destroyer - Logging System
Centralized logging with file and console output.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional
from config import USER_DATA_DIR, SERVER_MODE

# Log directory
LOG_DIR = os.path.join(USER_DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color for console
        if hasattr(record, 'use_color') and record.use_color:
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            record.msg = f"{color}{record.msg}{self.RESET}"

        return super().format(record)


class HHLogger:
    """
    Centralized logger for HeadHunter Destroyer.

    Features:
    - Console output (colored in desktop mode)
    - File logging with rotation
    - Session-based log files
    - Structured logging for actions
    """

    def __init__(self, name: str = "hh_destroyer"):
        self.name = name
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

        # Action counters for session
        self.stats = {
            "applications": 0,
            "skipped": 0,
            "filtered": 0,
            "errors": 0,
            "resumes_updated": 0,
        }

    def _setup_handlers(self):
        """Setup console and file handlers."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        if SERVER_MODE:
            # Simple format for TUI
            console_format = "%(asctime)s %(levelname)s %(message)s"
        else:
            # Colored format for desktop
            console_format = "%(asctime)s %(levelname)s %(message)s"

        console_formatter = ColoredFormatter(console_format, datefmt="%H:%M:%S")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler - main log
        main_log_file = os.path.join(LOG_DIR, f"hh_destroyer_{self.session_id}.log")
        file_handler = logging.FileHandler(main_log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = "%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s"
        file_handler.setFormatter(logging.Formatter(file_format))
        self.logger.addHandler(file_handler)

        # Actions log (CSV-like for easy parsing)
        self.actions_file = os.path.join(LOG_DIR, f"actions_{self.session_id}.log")
        self._init_actions_log()

    def _init_actions_log(self):
        """Initialize actions log file with header."""
        with open(self.actions_file, "w", encoding="utf-8") as f:
            f.write("timestamp|action|vacancy_id|title|employer|status|details\n")

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
        self.stats["errors"] += 1

    def critical(self, message: str):
        """Log critical message."""
        self.logger.critical(message)

    # ============ Structured Action Logging ============

    def log_application(
        self,
        vacancy_id: str,
        title: str,
        employer: str,
        status: str,
        details: str = ""
    ):
        """Log application action."""
        timestamp = datetime.now().isoformat()

        # Update stats
        if status == "applied":
            self.stats["applications"] += 1
            self.info(f"[APPLIED] {title} @ {employer}")
        elif status == "skipped":
            self.stats["skipped"] += 1
            self.debug(f"[SKIPPED] {title} @ {employer} ({details})")
        elif status == "filtered":
            self.stats["filtered"] += 1
            self.debug(f"[FILTERED] {title} @ {employer} ({details})")
        else:
            self.warning(f"[{status.upper()}] {title} @ {employer} ({details})")

        # Write to actions log
        self._write_action("apply", vacancy_id, title, employer, status, details)

    def log_resume_update(self, resume_id: str, title: str, status: str):
        """Log resume update action."""
        if status == "success":
            self.stats["resumes_updated"] += 1
            self.info(f"[RESUME] Updated: {title}")
        else:
            self.warning(f"[RESUME] Failed to update: {title}")

        self._write_action("resume_update", resume_id, title, "", status, "")

    def log_page_scan(self, page_num: int, vacancies_count: int):
        """Log page scan."""
        self.debug(f"[SCAN] Page {page_num}: {vacancies_count} vacancies")
        self._write_action("scan", "", f"page_{page_num}", "", "ok", str(vacancies_count))

    def log_filter_action(self, action: str, target: str, filter_type: str):
        """Log filter modification."""
        self.info(f"[FILTER] {action}: {target} ({filter_type})")
        self._write_action("filter", "", target, action, "ok", filter_type)

    def log_session_start(self):
        """Log session start."""
        self.info("=" * 50)
        self.info(f"Session started: {self.session_id}")
        self.info("=" * 50)
        self._write_action("session", "", "start", "", "ok", self.session_id)

    def log_session_end(self):
        """Log session end with summary."""
        self.info("=" * 50)
        self.info("Session Summary:")
        self.info(f"  Applications: {self.stats['applications']}")
        self.info(f"  Skipped: {self.stats['skipped']}")
        self.info(f"  Filtered: {self.stats['filtered']}")
        self.info(f"  Resumes Updated: {self.stats['resumes_updated']}")
        self.info(f"  Errors: {self.stats['errors']}")
        self.info("=" * 50)
        self._write_action("session", "", "end", "", "ok", str(self.stats))

    def _write_action(
        self,
        action: str,
        vacancy_id: str,
        title: str,
        employer: str,
        status: str,
        details: str
    ):
        """Write action to actions log file."""
        timestamp = datetime.now().isoformat()
        # Escape pipe characters
        title = title.replace("|", "-")
        employer = employer.replace("|", "-")
        details = details.replace("|", "-")

        line = f"{timestamp}|{action}|{vacancy_id}|{title}|{employer}|{status}|{details}\n"

        try:
            with open(self.actions_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def get_session_stats(self) -> dict:
        """Get current session statistics."""
        return self.stats.copy()

    def get_log_files(self) -> dict:
        """Get paths to log files."""
        return {
            "main_log": os.path.join(LOG_DIR, f"hh_destroyer_{self.session_id}.log"),
            "actions_log": self.actions_file,
            "log_dir": LOG_DIR,
        }


# Global logger instance
_logger: Optional[HHLogger] = None


def get_logger() -> HHLogger:
    """Get or create global logger instance."""
    global _logger
    if _logger is None:
        _logger = HHLogger()
    return _logger


def setup_logger(name: str = "hh_destroyer") -> HHLogger:
    """Setup and return logger (call at app start)."""
    global _logger
    _logger = HHLogger(name)
    return _logger


# Convenience functions
def log_info(message: str):
    get_logger().info(message)


def log_warning(message: str):
    get_logger().warning(message)


def log_error(message: str):
    get_logger().error(message)


def log_debug(message: str):
    get_logger().debug(message)
