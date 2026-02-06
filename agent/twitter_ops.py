"""
Twitter Operations (Simplified for Minimal Version)
====================================================
Handles Twitter posting with manual approval.

In the minimal version, tweets are queued for human review.
Full automation will be added via self-improvement.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger("TheConstituent.Twitter")

# Try to import Tweepy
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    logger.info("Tweepy not installed. Twitter will use queue-only mode.")


class TwitterOperations:
    """
    Twitter operations with manual approval workflow.

    In minimal mode:
    - Tweets are queued for human approval
    - Manual posting via Twitter UI
    - Full API integration added later via self-improvement
    - Tweets persisted to data/pending_tweets.json
    """

    # File path for persistent storage
    DATA_DIR = Path(__file__).parent.parent / "data"
    PENDING_FILE = DATA_DIR / "pending_tweets.json"
    POSTED_FILE = DATA_DIR / "posted_tweets.json"

    def __init__(self):
        """Initialize Twitter operations."""
        self._pending_tweets: List[Dict] = []
        self._posted_tweets: List[Dict] = []
        self._client = None
        self._api_connected = False
        self._next_id = 1

        # Ensure data directory exists
        self._ensure_data_dir()

        # Load persisted tweets
        self._load_tweets()

        # Try to connect if credentials exist
        if TWEEPY_AVAILABLE:
            self._try_connect()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load_tweets(self):
        """Load tweets from disk."""
        # Load pending tweets
        if self.PENDING_FILE.exists():
            try:
                with open(self.PENDING_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._pending_tweets = data.get("tweets", [])
                    self._next_id = data.get("next_id", 1)
                    logger.info(f"Loaded {len(self._pending_tweets)} pending tweets from disk")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading pending tweets: {e}")
                self._pending_tweets = []

        # Load posted tweets history
        if self.POSTED_FILE.exists():
            try:
                with open(self.POSTED_FILE, 'r', encoding='utf-8') as f:
                    self._posted_tweets = json.load(f)
                    logger.info(f"Loaded {len(self._posted_tweets)} posted tweets from disk")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading posted tweets: {e}")
                self._posted_tweets = []

    def _save_tweets(self):
        """Save tweets to disk."""
        try:
            # Save pending tweets with next_id
            with open(self.PENDING_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "tweets": self._pending_tweets,
                    "next_id": self._next_id,
                    "updated_at": datetime.utcnow().isoformat()
                }, f, indent=2)

            # Save posted tweets
            with open(self.POSTED_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._posted_tweets, f, indent=2)

            logger.debug("Tweets saved to disk")

        except IOError as e:
            logger.error(f"Error saving tweets: {e}")

    def _try_connect(self):
        """Attempt to connect to Twitter API."""
        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
        api_key = os.environ.get("TWITTER_API_KEY")
        api_secret = os.environ.get("TWITTER_API_SECRET")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
        access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

        if all([api_key, api_secret, access_token, access_secret]):
            try:
                auth = tweepy.OAuthHandler(api_key, api_secret)
                auth.set_access_token(access_token, access_secret)
                self._client = tweepy.API(auth)
                # Verify credentials
                self._client.verify_credentials()
                self._api_connected = True
                logger.info("Twitter API connected")
            except Exception as e:
                logger.warning(f"Twitter API connection failed: {e}")
        else:
            logger.info("Twitter credentials not configured - using queue mode")

    def is_connected(self) -> bool:
        """Check if Twitter API is connected."""
        return self._api_connected

    def queue_tweet(self, text: str, metadata: Optional[Dict] = None) -> str:
        """
        Add tweet to approval queue and persist to disk.

        Args:
            text: Tweet content
            metadata: Optional metadata (topic, context, etc.)

        Returns:
            Confirmation message
        """
        if len(text) > 280:
            return f"❌ Tweet too long ({len(text)} chars). Max 280."

        tweet_data = {
            "id": self._next_id,
            "text": text,
            "queued_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "status": "pending"
        }

        self._next_id += 1
        self._pending_tweets.append(tweet_data)

        # Persist to disk
        self._save_tweets()

        logger.info(f"Tweet queued and saved: {text[:50]}...")

        return f"✅ Tweet #{tweet_data['id']} queued for approval"

    def get_pending(self) -> List[Dict]:
        """Get all pending tweets."""
        return [t for t in self._pending_tweets if t["status"] == "pending"]

    def approve_tweet(self, tweet_id: int) -> str:
        """
        Approve a pending tweet.

        Args:
            tweet_id: ID of tweet to approve

        Returns:
            Status message
        """
        for tweet in self._pending_tweets:
            if tweet["id"] == tweet_id:
                tweet["status"] = "approved"
                tweet["approved_at"] = datetime.utcnow().isoformat()

                # Persist change
                self._save_tweets()

                # Try to post if API is connected
                if self._api_connected:
                    return self._post_tweet(tweet)
                else:
                    return f"✅ Tweet #{tweet_id} approved. Post manually:\n\n\"{tweet['text']}\""

        return f"❌ Tweet #{tweet_id} not found"

    def reject_tweet(self, tweet_id: int, reason: str = "") -> str:
        """
        Reject a pending tweet.

        Args:
            tweet_id: ID of tweet to reject
            reason: Optional rejection reason

        Returns:
            Status message
        """
        for tweet in self._pending_tweets:
            if tweet["id"] == tweet_id:
                tweet["status"] = "rejected"
                tweet["rejected_at"] = datetime.utcnow().isoformat()
                tweet["rejection_reason"] = reason

                # Persist change
                self._save_tweets()

                return f"✅ Tweet #{tweet_id} rejected"

        return f"❌ Tweet #{tweet_id} not found"

    def _post_tweet(self, tweet: Dict) -> str:
        """
        Post a tweet via API.

        Args:
            tweet: Tweet data dict

        Returns:
            Status message
        """
        if not self._api_connected:
            return "❌ Twitter API not connected"

        try:
            result = self._client.update_status(tweet["text"])
            tweet["status"] = "posted"
            tweet["posted_at"] = datetime.utcnow().isoformat()
            tweet["twitter_id"] = str(result.id)
            self._posted_tweets.append(tweet)

            # Persist changes
            self._save_tweets()

            logger.info(f"Tweet posted: {result.id}")
            return f"✅ Posted! Tweet ID: {result.id}"

        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return f"❌ Failed to post: {e}"

    def get_post_history(self) -> List[Dict]:
        """Get history of posted tweets."""
        return self._posted_tweets

    def clear_pending(self) -> str:
        """Clear all pending tweets."""
        count = len(self.get_pending())
        self._pending_tweets = [
            t for t in self._pending_tweets
            if t["status"] != "pending"
        ]

        # Persist change
        self._save_tweets()

        return f"✅ Cleared {count} pending tweets"

    def format_pending_list(self) -> str:
        """Format pending tweets for display."""
        pending = self.get_pending()

        if not pending:
            return "📭 No pending tweets"

        result = "📋 Pending Tweets:\n" + "-" * 40 + "\n"

        for tweet in pending:
            result += f"\n#{tweet['id']} (queued {tweet['queued_at'][:10]})\n"
            result += f"   \"{tweet['text'][:100]}{'...' if len(tweet['text']) > 100 else ''}\"\n"

        result += "\n" + "-" * 40
        result += "\nCommands: approve <id>, reject <id>, clear"

        return result

    def get_approved_tweets(self) -> List[Dict]:
        """Get all approved tweets waiting to be posted."""
        return [t for t in self._pending_tweets if t["status"] == "approved"]

    def post_queued_tweets(self) -> Dict:
        """
        Post all approved tweets to Twitter.

        Returns:
            Dict with posted count, failed count, and details
        """
        result = {
            "posted": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

        if not self._api_connected:
            # No API connection - skip posting but don't error
            approved = self.get_approved_tweets()
            result["skipped"] = len(approved)
            if approved:
                logger.info(f"Skipping {len(approved)} tweets - Twitter API not connected")
                result["details"].append("Twitter API not connected - tweets remain in queue")
            return result

        # Get approved tweets
        approved_tweets = self.get_approved_tweets()

        if not approved_tweets:
            logger.debug("No approved tweets to post")
            return result

        logger.info(f"Posting {len(approved_tweets)} approved tweets...")

        for tweet in approved_tweets:
            try:
                # Post to Twitter
                posted = self._client.update_status(tweet["text"])

                # Mark as posted
                tweet["status"] = "posted"
                tweet["posted_at"] = datetime.utcnow().isoformat()
                tweet["twitter_id"] = str(posted.id)
                self._posted_tweets.append(tweet)

                result["posted"] += 1
                result["details"].append(f"✅ Tweet #{tweet['id']} posted (ID: {posted.id})")
                logger.info(f"Posted tweet #{tweet['id']}: {posted.id}")

            except tweepy.TweepyException as e:
                # Twitter API error - keep in queue for retry
                result["failed"] += 1
                tweet["last_error"] = str(e)
                tweet["last_attempt"] = datetime.utcnow().isoformat()
                tweet["retry_count"] = tweet.get("retry_count", 0) + 1

                result["details"].append(f"❌ Tweet #{tweet['id']} failed: {e}")
                logger.error(f"Failed to post tweet #{tweet['id']}: {e}")

                # If too many retries, mark as failed permanently
                if tweet["retry_count"] >= 3:
                    tweet["status"] = "failed"
                    result["details"].append(f"   Tweet #{tweet['id']} marked as failed after 3 retries")

            except Exception as e:
                # Unexpected error - log but don't crash
                result["failed"] += 1
                result["details"].append(f"❌ Tweet #{tweet['id']} unexpected error: {e}")
                logger.error(f"Unexpected error posting tweet #{tweet['id']}: {e}")

        # Clean up posted tweets from pending list
        self._pending_tweets = [
            t for t in self._pending_tweets
            if t["status"] not in ["posted"]
        ]

        # Persist changes
        self._save_tweets()

        return result

    def get_failed_tweets(self) -> List[Dict]:
        """Get tweets that failed to post after retries."""
        return [t for t in self._pending_tweets if t["status"] == "failed"]

    def retry_failed_tweet(self, tweet_id: int) -> str:
        """
        Reset a failed tweet for retry.

        Args:
            tweet_id: ID of tweet to retry

        Returns:
            Status message
        """
        for tweet in self._pending_tweets:
            if tweet["id"] == tweet_id and tweet["status"] == "failed":
                tweet["status"] = "approved"
                tweet["retry_count"] = 0

                # Persist change
                self._save_tweets()

                return f"✅ Tweet #{tweet_id} reset for retry"

        return f"❌ Tweet #{tweet_id} not found or not in failed status"

    # =========================================================================
    # Draft Tweet Methods (for Telegram approval workflow)
    # =========================================================================

    def save_draft(self, chat_id: int, text: str, topic: str) -> Dict:
        """
        Save a draft tweet awaiting user approval.

        Args:
            chat_id: Telegram chat ID of the user
            text: The drafted tweet text
            topic: The topic/prompt used to generate the tweet

        Returns:
            The draft tweet dict
        """
        # Remove any existing draft for this chat
        self._pending_tweets = [
            t for t in self._pending_tweets
            if not (t.get("chat_id") == chat_id and t.get("status") == "draft")
        ]

        draft = {
            "id": self._next_id,
            "text": text,
            "topic": topic,
            "chat_id": chat_id,
            "status": "draft",
            "queued_at": datetime.utcnow().isoformat(),
            "metadata": {"source": "telegram"}
        }

        self._next_id += 1
        self._pending_tweets.append(draft)
        self._save_tweets()

        logger.info(f"Draft saved for chat {chat_id}: {text[:50]}...")
        return draft

    def get_draft(self, chat_id: int) -> Optional[Dict]:
        """
        Get the pending draft for a chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Draft dict or None if no draft exists
        """
        for tweet in self._pending_tweets:
            if tweet.get("chat_id") == chat_id and tweet.get("status") == "draft":
                return tweet
        return None

    def approve_draft(self, chat_id: int) -> Optional[Dict]:
        """
        Approve a draft tweet (change status to approved).

        Args:
            chat_id: Telegram chat ID

        Returns:
            The approved tweet dict or None if no draft found
        """
        for tweet in self._pending_tweets:
            if tweet.get("chat_id") == chat_id and tweet.get("status") == "draft":
                tweet["status"] = "approved"
                tweet["approved_at"] = datetime.utcnow().isoformat()
                self._save_tweets()
                logger.info(f"Draft approved for chat {chat_id}")
                return tweet
        return None

    def reject_draft(self, chat_id: int) -> Optional[Dict]:
        """
        Reject/discard a draft tweet.

        Args:
            chat_id: Telegram chat ID

        Returns:
            The rejected tweet dict or None if no draft found
        """
        for i, tweet in enumerate(self._pending_tweets):
            if tweet.get("chat_id") == chat_id and tweet.get("status") == "draft":
                rejected = self._pending_tweets.pop(i)
                rejected["status"] = "rejected"
                rejected["rejected_at"] = datetime.utcnow().isoformat()
                self._save_tweets()
                logger.info(f"Draft rejected for chat {chat_id}")
                return rejected
        return None

    def get_draft_count(self) -> int:
        """Get count of drafts awaiting approval."""
        return len([t for t in self._pending_tweets if t.get("status") == "draft"])

    def get_pending_count(self) -> int:
        """Get count of tweets pending (draft status, awaiting user approval)."""
        return len(self.get_pending())

    def get_approved_count(self) -> int:
        """Get count of approved tweets waiting to be posted."""
        return len(self.get_approved_tweets())

    def get_all_counts(self) -> Dict[str, int]:
        """Get all tweet counts by status."""
        counts = {
            "draft": 0,
            "pending": 0,
            "approved": 0,
            "failed": 0,
            "posted": len(self._posted_tweets)
        }
        for tweet in self._pending_tweets:
            status = tweet.get("status", "pending")
            if status in counts:
                counts[status] += 1
        return counts


