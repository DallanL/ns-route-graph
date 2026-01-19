import json
import os
import logging
import fnmatch
from typing import List
from urllib.parse import urlparse
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class DomainWhitelist:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.allowed_patterns: List[str] = []
        self._last_mtime = 0
        self.load_config()

    def load_config(self):
        """Loads or reloads the configuration if the file has changed."""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(
                    f"Whitelist config file not found at {self.config_path}. Defaulting to empty whitelist."
                )
                self.allowed_patterns = []
                return

            mtime = os.path.getmtime(self.config_path)
            if mtime > self._last_mtime:
                logger.info(f"Loading whitelist config from {self.config_path}")
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self.allowed_patterns = data.get("allowed_domains", [])
                self._last_mtime = mtime
                logger.debug(f"Loaded allowed patterns: {self.allowed_patterns}")
        except Exception as e:
            logger.error(f"Failed to load whitelist config: {e}")
            # Keep previous config on error to avoid outage

    def is_allowed(self, url: str) -> bool:
        """
        Checks if the provided URL hostname matches any of the allowed patterns.
        Handles checking for file updates before validation.
        """
        if not url:
            return False

        # Refresh config if needed
        self.load_config()

        # Parse hostname
        try:
            # Handle cases where url might not have scheme (though valid API URLs should)
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                logger.warning(f"Could not parse hostname from {url}")
                return False
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return False

        # Check against patterns
        for pattern in self.allowed_patterns:
            # fnmatch supports shell-style wildcards (*, ?, etc.)
            if fnmatch.fnmatch(hostname, pattern):
                return True

        logger.warning(f"URL {url} (hostname: {hostname}) denied by whitelist.")
        return False

    def validate_or_raise(self, url: str):
        """Helper that raises 403 if not allowed."""
        if not self.is_allowed(url):
            raise HTTPException(
                status_code=403, detail="API URL not in allowed whitelist."
            )
