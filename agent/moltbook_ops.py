"""
Moltbook Operations for The Constituent v2.3
==============================================
Handles interaction with Moltbook - the social network for AI agents.

v2.3 improvements:
- Intelligent rate limit pre-check (B): checks cooldown before API call
- 429 detection with retry info (B): returns structured retry_after
- Post ID validation before comment (D): validates post exists before commenting
- Last post time persistence across restarts

API Base: https://www.moltbook.com/api/v1
IMPORTANT: Always use www in the URL (without www, auth headers get stripped on redirect)
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger("TheConstituent.Moltbook")


class MoltbookOperations:
    """
    Moltbook API client for The Constituent.
    
    Handles:
    - Registration and authentication
    - Reading feed and posts
    - Posting content and comments
    - Searching for relevant discussions
    - Heartbeat (periodic check-in)
    
    Rate limits (Moltbook server-side):
    - 100 requests/minute
    - 1 post per 30 minutes
    - 50 comments/hour
    """

    BASE_URL = "https://www.moltbook.com/api/v1"
    DATA_DIR = Path(__file__).parent.parent / "data"
    CREDENTIALS_FILE = DATA_DIR / "moltbook_credentials.json"
    HISTORY_FILE = DATA_DIR / "moltbook_history.json"

    # Rate limit constants
    POST_COOLDOWN_MINUTES = 30
    COMMENT_COOLDOWN_SECONDS = 120  # 2 minutes

    def __init__(self):
        """Initialize Moltbook operations."""
        self._api_key: Optional[str] = None
        self._agent_id: Optional[str] = None
        self._agent_name: str = "TheConstituent"
        self._connected: bool = False
        self._last_post_time: Optional[datetime] = None
        self._last_comment_time: Optional[datetime] = None
        self._last_heartbeat: Optional[datetime] = None
        self._post_history: List[Dict] = []

        # Ensure data directory exists
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Try to load saved credentials
        self._load_credentials()

        # Try to load post history (also restores _last_post_time)
        self._load_history()

        # Test connection if we have credentials
        if self._api_key:
            self._test_connection()

    def _load_credentials(self):
        """Load Moltbook credentials from file or environment."""
        # Try environment variable first
        env_key = os.environ.get("MOLTBOOK_API_KEY")
        if env_key:
            self._api_key = env_key
            logger.info("Moltbook API key loaded from environment")
            return

        # Try credentials file
        if self.CREDENTIALS_FILE.exists():
            try:
                with open(self.CREDENTIALS_FILE, 'r') as f:
                    creds = json.load(f)
                    self._api_key = creds.get("api_key")
                    self._agent_id = creds.get("agent_id")
                    self._agent_name = creds.get("agent_name", "TheConstituent")
                    if self._api_key:
                        logger.info(f"Moltbook credentials loaded for {self._agent_name}")
                    return
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading Moltbook credentials: {e}")

        # Try knowledge file (legacy format)
        knowledge_file = Path("memory/knowledge/moltbook_credentials.md")
        if knowledge_file.exists():
            try:
                content = knowledge_file.read_text()
                for line in content.split("\n"):
                    if "API Key:" in line:
                        self._api_key = line.split("API Key:")[-1].strip()
                    if "Agent ID:" in line:
                        self._agent_id = line.split("Agent ID:")[-1].strip()
                if self._api_key:
                    logger.info("Moltbook credentials loaded from knowledge file")
                    self._save_credentials()
                    return
            except IOError:
                pass

        logger.info("No Moltbook credentials found")

    def _save_credentials(self):
        """Save credentials to file."""
        try:
            creds = {
                "api_key": self._api_key,
                "agent_id": self._agent_id,
                "agent_name": self._agent_name,
                "base_url": self.BASE_URL,
                "updated_at": datetime.utcnow().isoformat()
            }
            with open(self.CREDENTIALS_FILE, 'w') as f:
                json.dump(creds, f, indent=2)
            logger.info("Moltbook credentials saved")
        except IOError as e:
            logger.error(f"Error saving Moltbook credentials: {e}")

    def _load_history(self):
        """Load post history from file. Also restores _last_post_time."""
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    self._post_history = json.load(f)
                logger.info(f"Loaded {len(self._post_history)} Moltbook history entries")

                # Restore _last_post_time from most recent post in history
                for entry in reversed(self._post_history):
                    if entry.get("type") == "post" and entry.get("timestamp"):
                        try:
                            self._last_post_time = datetime.fromisoformat(entry["timestamp"])
                            logger.info(f"Restored last post time: {self._last_post_time}")
                            break
                        except (ValueError, TypeError):
                            pass

                # Restore _last_comment_time from most recent comment
                for entry in reversed(self._post_history):
                    if entry.get("type") == "comment" and entry.get("timestamp"):
                        try:
                            self._last_comment_time = datetime.fromisoformat(entry["timestamp"])
                            break
                        except (ValueError, TypeError):
                            pass

            except (json.JSONDecodeError, IOError):
                self._post_history = []

    def _save_history(self):
        """Save post history to file."""
        try:
            with open(self.HISTORY_FILE, 'w') as f:
                json.dump(self._post_history[-100:], f, indent=2)
        except IOError as e:
            logger.error(f"Error saving Moltbook history: {e}")

    def _headers(self) -> dict:
        """Get authentication headers."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

    def _test_connection(self) -> bool:
        """Test if current API key is valid."""
        try:
            r = requests.get(
                f"{self.BASE_URL}/posts",
                headers=self._headers(),
                params={"sort": "hot", "limit": 1},
                timeout=10
            )
            if r.status_code == 200:
                self._connected = True
                logger.info("Moltbook API connection verified")
                return True
            elif r.status_code == 401:
                logger.warning("Moltbook API key is invalid or expired")
                self._connected = False
                return False
            else:
                logger.warning(f"Moltbook API returned {r.status_code}: {r.text[:200]}")
                self._connected = False
                return False
        except requests.RequestException as e:
            logger.error(f"Moltbook connection test failed: {e}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if Moltbook is connected."""
        return self._connected

    # =========================================================================
    # Rate Limit Pre-Check (Feature B)
    # =========================================================================

    def can_post(self) -> Dict:
        """
        Check if we can post right now.
        
        Returns:
            {
                "can_post": bool,
                "wait_minutes": int (0 if can post),
                "next_post_at": str (ISO timestamp, None if can post now)
            }
        """
        if not self._last_post_time:
            return {"can_post": True, "wait_minutes": 0, "next_post_at": None}

        elapsed = datetime.utcnow() - self._last_post_time
        cooldown = timedelta(minutes=self.POST_COOLDOWN_MINUTES)

        if elapsed >= cooldown:
            return {"can_post": True, "wait_minutes": 0, "next_post_at": None}

        remaining = cooldown - elapsed
        wait_min = int(remaining.total_seconds() / 60) + 1
        next_at = (self._last_post_time + cooldown).isoformat()

        return {
            "can_post": False,
            "wait_minutes": wait_min,
            "next_post_at": next_at
        }

    def can_comment(self) -> Dict:
        """Check if we can comment right now."""
        if not self._last_comment_time:
            return {"can_comment": True, "wait_seconds": 0}

        elapsed = datetime.utcnow() - self._last_comment_time
        cooldown = timedelta(seconds=self.COMMENT_COOLDOWN_SECONDS)

        if elapsed >= cooldown:
            return {"can_comment": True, "wait_seconds": 0}

        remaining = cooldown - elapsed
        return {
            "can_comment": False,
            "wait_seconds": int(remaining.total_seconds()) + 1
        }

    # =========================================================================
    # Post ID Validation (Feature D)
    # =========================================================================

    def validate_post_id(self, post_id: str) -> bool:
        """
        Check if a post ID exists on Moltbook.
        
        Args:
            post_id: The post ID to validate
            
        Returns:
            True if the post exists, False otherwise
        """
        if not self._api_key:
            return False

        try:
            r = requests.get(
                f"{self.BASE_URL}/posts/{post_id}",
                headers=self._headers(),
                timeout=10
            )
            return r.status_code == 200
        except requests.RequestException:
            return False

    # =========================================================================
    # Registration
    # =========================================================================

    def register(self, name: str = "TheConstituent",
                 description: str = "Constitutional facilitator for The Agents Republic.") -> Dict:
        """Register a new agent on Moltbook."""
        try:
            r = requests.post(
                f"{self.BASE_URL}/agents/register",
                json={"name": name, "description": description},
                timeout=15
            )

            result = {
                "status_code": r.status_code,
                "success": r.status_code == 201,
                "response": r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text
            }

            if r.status_code == 201:
                data = r.json()
                self._api_key = data.get("api_key")
                self._agent_id = data.get("id")
                self._agent_name = name
                self._save_credentials()
                self._connected = True
                logger.info(f"Successfully registered on Moltbook as {name}")
            elif r.status_code == 409:
                logger.warning(f"Name '{name}' already taken on Moltbook")
            else:
                logger.error(f"Registration failed: {r.status_code} {r.text}")

            return result

        except requests.RequestException as e:
            logger.error(f"Registration request failed: {e}")
            return {"status_code": 0, "success": False, "error": str(e)}

    # =========================================================================
    # Reading
    # =========================================================================

    def get_feed(self, sort: str = "hot", limit: int = 10) -> List[Dict]:
        """Get posts from Moltbook feed."""
        if not self._api_key:
            logger.warning("Cannot get feed: no API key")
            return []

        try:
            r = requests.get(
                f"{self.BASE_URL}/posts",
                headers=self._headers(),
                params={"sort": sort, "limit": min(limit, 25)},
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                posts = data.get("posts", data) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(posts)} posts from Moltbook ({sort})")
                return posts
            else:
                logger.error(f"Feed fetch failed: {r.status_code} {r.text[:200]}")
                return []
        except requests.RequestException as e:
            logger.error(f"Feed fetch error: {e}")
            return []

    def get_post(self, post_id: str) -> Optional[Dict]:
        """Get a specific post by ID."""
        if not self._api_key:
            return None

        try:
            r = requests.get(
                f"{self.BASE_URL}/posts/{post_id}",
                headers=self._headers(),
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
            return None
        except requests.RequestException as e:
            logger.error(f"Post fetch error: {e}")
            return None

    def get_comments(self, post_id: str, sort: str = "top") -> List[Dict]:
        """Get comments on a post."""
        if not self._api_key:
            return []

        try:
            r = requests.get(
                f"{self.BASE_URL}/posts/{post_id}/comments",
                headers=self._headers(),
                params={"sort": sort},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("comments", data) if isinstance(data, dict) else data
            return []
        except requests.RequestException as e:
            logger.error(f"Comments fetch error: {e}")
            return []

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search Moltbook posts."""
        if not self._api_key:
            return []

        try:
            r = requests.get(
                f"{self.BASE_URL}/search",
                headers=self._headers(),
                params={"q": query, "limit": limit},
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", data) if isinstance(data, dict) else data
                logger.info(f"Search '{query}': {len(results)} results")
                return results
            return []
        except requests.RequestException as e:
            logger.error(f"Search error: {e}")
            return []

    def get_profile(self, name: str = None) -> Optional[Dict]:
        """Get agent profile."""
        if not self._api_key:
            return None

        try:
            params = {"name": name} if name else {}
            r = requests.get(
                f"{self.BASE_URL}/agents/profile",
                headers=self._headers(),
                params=params,
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
            return None
        except requests.RequestException as e:
            logger.error(f"Profile fetch error: {e}")
            return None

    # =========================================================================
    # Writing
    # =========================================================================

    def create_post(self, title: str, content: str, submolt: str = "general") -> Dict:
        """
        Create a new post on Moltbook.
        
        Pre-checks local rate limit before calling API.
        Detects 429 from server and returns structured retry info.
        
        Rate limit: 1 post per 30 minutes.
        """
        if not self._api_key:
            return {"success": False, "error": "No API key configured"}

        # Pre-check local rate limit (Feature B)
        rate_check = self.can_post()
        if not rate_check["can_post"]:
            wait = rate_check["wait_minutes"]
            next_at = rate_check["next_post_at"]
            logger.info(f"Post rate limited locally. Wait {wait} minutes (next: {next_at})")
            return {
                "success": False,
                "status_code": 429,
                "error": f"Rate limited. Wait {wait} minutes.",
                "retry_after_minutes": wait,
                "next_post_at": next_at,
                "rate_limited": True  # Flag for ActionQueue retry
            }

        try:
            r = requests.post(
                f"{self.BASE_URL}/posts",
                headers=self._headers(),
                json={
                    "submolt": submolt,
                    "title": title,
                    "content": content
                },
                timeout=15
            )

            result = {
                "status_code": r.status_code,
                "success": r.status_code in [200, 201],
            }

            try:
                result["response"] = r.json()
            except ValueError:
                result["response"] = r.text

            if result["success"]:
                self._last_post_time = datetime.utcnow()
                self._post_history.append({
                    "type": "post",
                    "title": title,
                    "submolt": submolt,
                    "timestamp": datetime.utcnow().isoformat(),
                    "response": result["response"]
                })
                self._save_history()
                logger.info(f"Posted to m/{submolt}: {title}")

            elif r.status_code == 429:
                # Server rate limit — extract retry info
                resp = result.get("response", {})
                retry_min = 30
                if isinstance(resp, dict):
                    retry_min = resp.get("retry_after_minutes", 30)
                    hint = resp.get("hint", "")
                    # Parse "Wait X minutes" from hint
                    import re
                    m = re.search(r'(\d+)\s*minute', hint)
                    if m:
                        retry_min = int(m.group(1))

                # Update local tracker to match server
                self._last_post_time = datetime.utcnow() - timedelta(minutes=30 - retry_min)

                result["error"] = f"Server rate limit. Retry in {retry_min} minutes."
                result["retry_after_minutes"] = retry_min
                result["next_post_at"] = (datetime.utcnow() + timedelta(minutes=retry_min)).isoformat()
                result["rate_limited"] = True
                logger.warning(f"Post rate limited by server. Retry in {retry_min}min")

            else:
                logger.error(f"Post failed: {r.status_code} {r.text[:200]}")

            return result

        except requests.RequestException as e:
            logger.error(f"Post error: {e}")
            return {"success": False, "error": str(e)}

    def verify_post(self, verification_code: str, answer: str) -> Dict:
        """Verify a post with anti-spam challenge."""
        if not self._api_key:
            return {"success": False, "error": "No API key configured"}

        try:
            r = requests.post(
                f"{self.BASE_URL}/verify",
                headers=self._headers(),
                json={
                    "verification_code": verification_code,
                    "answer": answer
                },
                timeout=10
            )

            result = {
                "status_code": r.status_code,
                "success": r.status_code in [200, 201],
            }

            try:
                result["response"] = r.json()
            except ValueError:
                result["response"] = r.text

            if result["success"]:
                logger.info("Post verification successful")
            else:
                logger.error(f"Post verification failed: {r.status_code} {r.text[:200]}")

            return result

        except requests.RequestException as e:
            logger.error(f"Verification error: {e}")
            return {"success": False, "error": str(e)}

    def create_comment(self, post_id: str, content: str, parent_id: str = None) -> Dict:
        """
        Comment on a post.
        
        Pre-validates post ID (Feature D) and checks comment cooldown.
        Rate limit: 50 comments/hour, 2 min cooldown.
        """
        if not self._api_key:
            return {"success": False, "error": "No API key configured"}

        # Pre-validate post ID (Feature D)
        if not self.validate_post_id(post_id):
            logger.warning(f"Comment aborted: post {post_id} does not exist (404)")
            return {
                "success": False,
                "error": f"Post {post_id} not found. Cannot comment on non-existent post.",
                "invalid_post_id": True
            }

        # Pre-check comment cooldown
        comment_check = self.can_comment()
        if not comment_check["can_comment"]:
            wait = comment_check["wait_seconds"]
            logger.info(f"Comment rate limited. Wait {wait} seconds.")
            return {
                "success": False,
                "error": f"Comment cooldown. Wait {wait} seconds.",
                "rate_limited": True,
                "retry_after_seconds": wait
            }

        try:
            body = {"content": content}
            if parent_id:
                body["parent_id"] = parent_id

            r = requests.post(
                f"{self.BASE_URL}/posts/{post_id}/comments",
                headers=self._headers(),
                json=body,
                timeout=10
            )

            result = {
                "status_code": r.status_code,
                "success": r.status_code in [200, 201],
            }

            try:
                result["response"] = r.json()
            except ValueError:
                result["response"] = r.text

            if result["success"]:
                self._last_comment_time = datetime.utcnow()
                self._post_history.append({
                    "type": "comment",
                    "post_id": post_id,
                    "content": content[:100],
                    "timestamp": datetime.utcnow().isoformat()
                })
                self._save_history()
                logger.info(f"Commented on post {post_id}")
            elif r.status_code == 429:
                result["rate_limited"] = True
                result["error"] = "Comment rate limited by server"
                logger.warning(f"Comment rate limited by server on {post_id}")
            else:
                logger.error(f"Comment failed: {r.status_code} {r.text[:200]}")

            return result

        except requests.RequestException as e:
            logger.error(f"Comment error: {e}")
            return {"success": False, "error": str(e)}

    def upvote(self, post_id: str) -> Dict:
        """Upvote a post."""
        if not self._api_key:
            return {"success": False, "error": "No API key configured"}

        try:
            r = requests.post(
                f"{self.BASE_URL}/posts/{post_id}/upvote",
                headers=self._headers(),
                timeout=10
            )
            return {
                "status_code": r.status_code,
                "success": r.status_code in [200, 201],
            }
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Heartbeat (periodic check-in)
    # =========================================================================

    def heartbeat(self) -> Dict:
        """
        Perform a Moltbook heartbeat:
        1. Check feed for new posts
        2. Look for mentions or relevant discussions
        3. Return summary for the agent to process
        """
        if not self._connected:
            return {"success": False, "error": "Not connected to Moltbook"}

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "feed_posts": [],
            "mentions": [],
            "relevant": [],
        }

        try:
            feed = self.get_feed(sort="new", limit=10)
            result["feed_posts"] = feed

            mentions = self.search("TheConstituent", limit=5)
            result["mentions"] = mentions

            constitutional = self.search("constitution governance rights", limit=5)
            result["relevant"] = constitutional

            self._last_heartbeat = datetime.utcnow()
            result["success"] = True

            # Include rate limit status for agent awareness
            result["can_post"] = self.can_post()

            logger.info(f"Heartbeat: {len(feed)} feed, {len(mentions)} mentions, {len(constitutional)} relevant")

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            result["success"] = False
            result["error"] = str(e)

        return result

    # =========================================================================
    # Status
    # =========================================================================

    def get_status(self) -> Dict:
        """Get Moltbook connection status."""
        rate = self.can_post()
        return {
            "connected": self._connected,
            "agent_name": self._agent_name,
            "agent_id": self._agent_id,
            "has_api_key": bool(self._api_key),
            "last_post": self._last_post_time.isoformat() if self._last_post_time else None,
            "last_heartbeat": self._last_heartbeat.isoformat() if self._last_heartbeat else None,
            "posts_in_history": len(self._post_history),
            "can_post": rate["can_post"],
            "wait_minutes": rate.get("wait_minutes", 0),
        }
