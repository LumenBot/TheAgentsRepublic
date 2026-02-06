"""
Moltbook Operations for The Constituent v2.3 + v3.0 fix
========================================================
Handles interaction with Moltbook - the social network for AI agents.

v2.3 improvements:
- Intelligent rate limit pre-check (B): checks cooldown before API call
- 429 detection with retry info (B): returns structured retry_after
- Post ID validation before comment (D): validates post exists before commenting
- Last post time persistence across restarts

v3.0 fix:
- Corrected agent_name: XTheConstituent (was TheConstituent)
- Fixed search mentions to use correct username

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
        self._agent_name: str = "XTheConstituent"  # FIXED v3.0: was "TheConstituent"
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
                    self._agent_name = creds.get("agent_name", "XTheConstituent")  # FIXED v3.0
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
        Pre-check if agent can post (local rate limit tracking).
        
        Returns dict with:
        - can_post (bool)
        - wait_minutes (int, if rate limited)
        - last_post (str, ISO timestamp)
        - next_post_at (str, ISO timestamp)
        """
        if not self._last_post_time:
            return {
                "can_post": True,
                "wait_minutes": 0,
                "last_post": None,
                "next_post_at": datetime.utcnow().isoformat()
            }

        elapsed = datetime.utcnow() - self._last_post_time
        wait_minutes = self.POST_COOLDOWN_MINUTES - int(elapsed.total_seconds() / 60)

        if wait_minutes <= 0:
            return {
                "can_post": True,
                "wait_minutes": 0,
                "last_post": self._last_post_time.isoformat(),
                "next_post_at": datetime.utcnow().isoformat()
            }

        next_post = self._last_post_time + timedelta(minutes=self.POST_COOLDOWN_MINUTES)
        return {
            "can_post": False,
            "wait_minutes": wait_minutes,
            "last_post": self._last_post_time.isoformat(),
            "next_post_at": next_post.isoformat()
        }

    def can_comment(self) -> Dict:
        """
        Pre-check if agent can comment (2 min cooldown).
        
        Returns dict with:
        - can_comment (bool)
        - wait_seconds (int)
        """
        if not self._last_comment_time:
            return {"can_comment": True, "wait_seconds": 0}

        elapsed = datetime.utcnow() - self._last_comment_time
        wait_seconds = self.COMMENT_COOLDOWN_SECONDS - int(elapsed.total_seconds())

        if wait_seconds <= 0:
            return {"can_comment": True, "wait_seconds": 0}

        return {"can_comment": False, "wait_seconds": wait_seconds}

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get_feed(self, sort: str = "hot", limit: int = 20) -> List[Dict]:
        """
        Get posts from the main feed.
        
        Args:
            sort: 'hot', 'new', 'top'
            limit: max posts to return (1-100)
        """
        if not self._api_key:
            logger.warning("Cannot get feed: no API key")
            return []

        try:
            r = requests.get(
                f"{self.BASE_URL}/posts",
                headers=self._headers(),
                params={"sort": sort, "limit": min(limit, 100)},
                timeout=10
            )
            if r.status_code == 200:
                posts = r.json()
                logger.info(f"Retrieved {len(posts)} posts from feed (sort={sort})")
                return posts
            else:
                logger.error(f"Feed error: {r.status_code} {r.text[:200]}")
                return []
        except requests.RequestException as e:
            logger.error(f"Feed request failed: {e}")
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
            elif r.status_code == 404:
                logger.warning(f"Post {post_id} not found (404)")
                return None
            else:
                logger.error(f"Get post error: {r.status_code} {r.text[:200]}")
                return None
        except requests.RequestException as e:
            logger.error(f"Get post request failed: {e}")
            return None

    def get_post_with_comments(self, post_id: str, include_all: bool = True) -> Optional[Dict]:
        """
        Get a post with ALL its comments.
        
        Args:
            post_id: Post ID to fetch
            include_all: If True, fetches all comments (may require pagination)
        
        Returns:
            Dict with post data + 'comments' list, or None if error
            
        Example:
            post = moltbook.get_post_with_comments("abc123")
            if post:
                comments = post.get("comments", [])
                for comment in comments:
                    print(comment["author"], comment["content"])
        """
        if not self._api_key:
            logger.warning("Cannot get post: no API key")
            return None

        try:
            # First, get the post
            post = self.get_post(post_id)
            if not post:
                return None
            
            # Then fetch comments (may be separate endpoint)
            # Try: /posts/{post_id}/comments
            try:
                r = requests.get(
                    f"{self.BASE_URL}/posts/{post_id}/comments",
                    headers=self._headers(),
                    timeout=10
                )
                
                if r.status_code == 200:
                    comments = r.json()
                    
                    # Handle pagination if necessary
                    if include_all and isinstance(comments, dict):
                        # If API returns paginated response
                        all_comments = comments.get("comments", [])
                        next_cursor = comments.get("next_cursor")
                        
                        while next_cursor:
                            r_next = requests.get(
                                f"{self.BASE_URL}/posts/{post_id}/comments",
                                headers=self._headers(),
                                params={"cursor": next_cursor},
                                timeout=10
                            )
                            if r_next.status_code == 200:
                                next_data = r_next.json()
                                all_comments.extend(next_data.get("comments", []))
                                next_cursor = next_data.get("next_cursor")
                            else:
                                break
                        
                        post["comments"] = all_comments
                    elif isinstance(comments, list):
                        # Direct list of comments
                        post["comments"] = comments
                    else:
                        post["comments"] = []
                    
                    logger.info(f"Retrieved post {post_id} with {len(post.get('comments', []))} comments")
                    
                elif r.status_code == 404:
                    # Comments endpoint doesn't exist, try embedded in post
                    logger.info(f"No separate comments endpoint, using embedded comments")
                    post["comments"] = post.get("comments", [])
                    
                else:
                    logger.warning(f"Comments fetch returned {r.status_code}, using embedded")
                    post["comments"] = post.get("comments", [])
                    
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch comments separately: {e}, using embedded")
                post["comments"] = post.get("comments", [])
            
            return post
            
        except Exception as e:
            logger.error(f"Get post with comments failed: {e}")
            return None

    def get_profile(self, agent_name: str = None) -> Optional[Dict]:
        """Get agent profile (defaults to self)."""
        if not self._api_key:
            return None

        username = agent_name or self._agent_name

        try:
            r = requests.get(
                f"{self.BASE_URL}/users/{username}",
                headers=self._headers(),
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 404:
                logger.warning(f"Profile {username} not found")
                return None
            else:
                logger.error(f"Profile error: {r.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"Profile request failed: {e}")
            return None

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for posts matching query."""
        if not self._api_key:
            return []

        try:
            # Ensure limit is int (fix for type comparison error)
            limit = int(limit) if limit else 10
            
            r = requests.get(
                f"{self.BASE_URL}/search",
                headers=self._headers(),
                params={"q": query, "limit": min(limit, 50)},
                timeout=10
            )
            if r.status_code == 200:
                results = r.json()
                logger.info(f"Search '{query}': {len(results)} results")
                return results
            else:
                logger.error(f"Search error: {r.status_code}")
                return []
        except requests.RequestException as e:
            logger.error(f"Search request failed: {e}")
            return []

    # =========================================================================
    # Post ID Validation (Feature D)
    # =========================================================================

    def validate_post_id(self, post_id: str) -> bool:
        """
        Validate that a post ID exists before attempting to comment.
        
        Returns:
            True if post exists (200 OK)
            False if post not found (404) or error
        """
        if not self._api_key:
            logger.warning("Cannot validate post: no API key")
            return False

        try:
            r = requests.get(
                f"{self.BASE_URL}/posts/{post_id}",
                headers=self._headers(),
                timeout=10
            )
            if r.status_code == 200:
                logger.debug(f"Post {post_id} validated (exists)")
                return True
            elif r.status_code == 404:
                logger.warning(f"Post {post_id} does not exist (404)")
                return False
            else:
                logger.error(f"Post validation error {r.status_code}: {r.text[:100]}")
                return False
        except requests.RequestException as e:
            logger.error(f"Post validation request failed: {e}")
            return False

    # =========================================================================
    # Write Operations
    # =========================================================================

    def create_post(self, title: str, content: str, submolt: str = None) -> Dict:
        """
        Create a new post on Moltbook.
        
        Pre-checks rate limit (Feature B) and handles 429 responses.
        
        Args:
            title: Post title
            content: Post body (markdown supported)
            submolt: Optional submolt name (e.g., "m/technology")
        
        Returns:
            Dict with:
            - success (bool)
            - post_id (str, if successful)
            - url (str, if successful)
            - error (str, if failed)
            - rate_limited (bool, if 429)
            - retry_after_minutes (int, if 429)
        """
        if not self._api_key:
            return {"success": False, "error": "No API key configured"}

        # Pre-check local rate limit (Feature B)
        rate_check = self.can_post()
        if not rate_check["can_post"]:
            wait = rate_check["wait_minutes"]
            logger.info(f"Post rate limited (local check). Wait {wait} minutes.")
            return {
                "success": False,
                "error": f"Post cooldown. Wait {wait} minutes.",
                "rate_limited": True,
                "retry_after_minutes": wait,
                "next_post_at": rate_check["next_post_at"]
            }

        try:
            body = {
                "title": title,
                "content": content
            }
            if submolt:
                body["submolt"] = submolt

            r = requests.post(
                f"{self.BASE_URL}/posts",
                headers=self._headers(),
                json=body,
                timeout=10
            )

            result = {
                "status_code": r.status_code,
                "success": r.status_code in [200, 201],
            }

            try:
                response_data = r.json()
                result["response"] = response_data
            except ValueError:
                result["response"] = r.text

            if result["success"]:
                # Extract post ID and construct URL
                post_id = response_data.get("id") or response_data.get("post_id")
                result["post_id"] = post_id
                result["url"] = f"https://www.moltbook.com/post/{post_id}"
                
                # Update local state
                self._last_post_time = datetime.utcnow()
                self._post_history.append({
                    "type": "post",
                    "post_id": post_id,
                    "title": title,
                    "timestamp": datetime.utcnow().isoformat()
                })
                self._save_history()
                
                logger.info(f"Post created: {post_id} ({title[:50]})")

            elif r.status_code == 429:
                # Server-side rate limit (Feature B)
                result["rate_limited"] = True
                
                # Try to parse retry time from response
                retry_min = 30  # default
                if "retry" in r.text.lower():
                    import re
                    m = re.search(r'(\d+)\s*min', r.text.lower())
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

            mentions = self.search("XTheConstituent", limit=5)  # FIXED v3.0: was "TheConstituent"
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
