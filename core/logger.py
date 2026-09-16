"""
Centralized Logging Module with Configurable Day-Wise File Generation.
Provides unified console and file logging timelines for both API and UI test suites.
"""
import os
import re
import logging
from datetime import datetime, timedelta


# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Ensure logs folder exists
os.makedirs(LOG_DIR, exist_ok=True)

# Dynamically resolve today's date-stamped filename (e.g. framework-2026-09-10.log)
today_date_str = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(LOG_DIR, f"framework-{today_date_str}.log")

# Load central configurations with resilient fallbacks
try:
    from core.config import Config
    log_level_name = Config.LOG_LEVEL.upper()
    retention_days = Config.LOG_RETENTION_DAYS
    screenshot_retention_days = Config.SCREENSHOT_RETENTION_DAYS
except Exception:
    log_level_name = "DEBUG"
    retention_days = 7
    screenshot_retention_days = 7

# Map string name to logging level object
log_level = getattr(logging, log_level_name, logging.DEBUG)

# Configure logger
logger = logging.getLogger("FitNessePythonFramework")
logger.setLevel(logging.DEBUG)  # Root level set to capture all details

# Clear existing handlers to avoid duplicates
if logger.hasHandlers():
    logger.handlers.clear()

# Create standard formatting
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 1. Console Handler (Prints clean, readable info in terminal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 2. File Handler (Generates direct day-wise log files)
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(log_level)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# ── Dynamic Log File Retention Cleanup Helper ──
def cleanup_old_logs(log_directory: str, max_days: int) -> None:
    """
    Scans the logs directory and automatically deletes any date-stamped
    log files older than the specified max_days retention limit.
    """
    try:
        import glob
        pattern = os.path.join(log_directory, "framework-*.log")
        log_files = glob.glob(pattern)
        
        cutoff_date = datetime.now() - timedelta(days=max_days)
        deleted_count = 0
        
        for file_path in log_files:
            file_name = os.path.basename(file_path)
            # Match date segment: framework-YYYY-MM-DD.log
            match = re.search(r'framework-(\d{4}-\d{2}-\d{2})\.log', file_name)
            if match:
                file_date_str = match.group(1)
                try:
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        os.remove(file_path)
                        deleted_count += 1
                except ValueError:
                    pass  # Skip malformed dates
                    
        if deleted_count > 0:
            logger.info(f"[LOGGER] Cleaned up {deleted_count} log files older than {max_days} days.")
    except Exception as e:
        # Graceful non-blocking fallback if os permissions or script fails
        print(f"[LOGGER WARNING] Log file cleanup failed: {e}")


def cleanup_old_screenshots(screenshot_directory: str, max_days: int) -> None:
    """
    Scans the UI automation screenshots folder on load and automatically
    deletes any captured failure screenshots older than the retention days limit.
    """
    try:
        if not os.path.exists(screenshot_directory):
            return
            
        import glob
        pattern = os.path.join(screenshot_directory, "*.png")
        screenshot_files = glob.glob(pattern)
        
        cutoff_date = datetime.now() - timedelta(days=max_days)
        deleted_count = 0
        
        for file_path in screenshot_files:
            try:
                # Check modification time of file on disk
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mtime < cutoff_date:
                    os.remove(file_path)
                    deleted_count += 1
            except Exception:
                pass
                
        if deleted_count > 0:
            logger.info(f"[LOGGER] Cleaned up {deleted_count} screenshot files older than {max_days} days.")
    except Exception as e:
        print(f"[LOGGER WARNING] Screenshot cleanup failed: {e}")


# Run log and screenshot files cleanups automatically on logger load!
cleanup_old_logs(LOG_DIR, retention_days)
cleanup_old_screenshots(os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "ui-automation"), screenshot_retention_days)


def log_request(method: str, url: str, headers: dict = None, payload: dict = None) -> None:
    """Logs the HTTP request details in a structured format."""
    logger.info(f"---> HTTP REQUEST: {method} {url}")
    if headers:
        logger.debug(f"Request Headers: {headers}")
    if payload:
        logger.debug(f"Request Payload: {payload}")


def log_response(status_code: int, response_text: str, response_headers: dict = None) -> None:
    """Logs the HTTP response details in a structured format."""
    logger.info(f"<--- HTTP RESPONSE: Status Code {status_code}")
    if response_headers:
        logger.debug(f"Response Headers: {response_headers}")
    if response_text:
        # Limit logging size of responses to keep logs clean
        truncated_text = response_text[:1000] + "..." if len(response_text) > 1000 else response_text
        logger.debug(f"Response Body: {truncated_text}")
