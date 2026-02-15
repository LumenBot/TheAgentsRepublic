"""
Base Integration — Abstract class for platform connectors.
============================================================
All integrations follow this pattern for consistency.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger("TheConstituent.Integration")


class BaseIntegration(ABC):
    """Abstract base for all platform integrations."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'moltbook', 'twitter')."""
        ...

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection. Returns True if successful."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if currently connected."""
        ...

    @abstractmethod
    def post_content(self, content: str, **kwargs) -> Dict:
        """Publish content to the platform."""
        ...

    @abstractmethod
    def read_feed(self, limit: int = 10) -> List[Dict]:
        """Read recent feed items."""
        ...

    @abstractmethod
    def engage(self, post_id: str, action: str = "like", **kwargs) -> Dict:
        """Engage with a post (like, comment, repost)."""
        ...

    def get_status(self) -> Dict:
        """Get integration status."""
        return {
            "platform": self.platform_name,
            "connected": self.is_connected(),
        }
