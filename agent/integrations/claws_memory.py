"""
CLAWS Integration — Clawnch Long-term Agentic Working Storage
==============================================================
HTTP API client for the CLAWS memory system.
Provides persistent, searchable memory with semantic search and tagging.

API: https://clawn.ch/api/memory
Actions: remember, recall, recent, forget, tag, stats, context
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any

import requests

logger = logging.getLogger("TheConstituent.Integration.CLAWS")

CLAWS_API_URL = "https://clawn.ch/api/memory"
CLAWS_TIMEOUT = 15  # seconds


class ClawsMemory:
    """Client for the CLAWS (Clawnch Long-term Agentic Working Storage) API."""

    def __init__(self, agent_id: str = None, api_key: str = None):
        self.agent_id = agent_id or os.environ.get(
            "CLAWS_AGENT_ID",
            os.environ.get("MOLTBOOK_AGENT_ID", "the-constituent"),
        )
        self.api_key = api_key or os.environ.get("CLAWS_API_KEY", "")
        self._connected = False
        self._last_error = None

    # ------------------------------------------------------------------
    # Low-level API
    # ------------------------------------------------------------------

    def _request(self, action: str, **kwargs) -> Dict:
        """Send a request to the CLAWS API."""
        payload = {"action": action, "agentId": self.agent_id, **kwargs}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = requests.post(
                CLAWS_API_URL,
                json=payload,
                headers=headers,
                timeout=CLAWS_TIMEOUT,
            )
            self._connected = True
            self._last_error = None

            if resp.status_code == 200:
                return resp.json()
            else:
                error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                self._last_error = error
                logger.warning(f"CLAWS API error: {error}")
                return {"error": error}
        except requests.exceptions.Timeout:
            self._last_error = "timeout"
            logger.warning("CLAWS API timeout")
            return {"error": "Request timed out"}
        except requests.exceptions.ConnectionError as e:
            self._last_error = str(e)
            logger.warning(f"CLAWS connection error: {e}")
            return {"error": f"Connection failed: {e}"}
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"CLAWS unexpected error: {e}")
            return {"error": str(e)}

    def is_connected(self) -> bool:
        """Check connectivity (tries stats if not yet tested)."""
        if not self._connected:
            result = self.stats()
            return "error" not in result
        return self._connected

    # ------------------------------------------------------------------
    # Memory Operations
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[float] = None,
        thread_id: Optional[str] = None,
    ) -> Dict:
        """Store a memory in CLAWS.

        Args:
            content: The memory text to store.
            metadata: Optional key-value metadata (e.g., {"source": "telegram"}).
            tags: Optional list of tags for categorization.
            importance: Optional importance score (0.0-1.0).
            thread_id: Optional thread ID for grouping related memories.
        """
        kwargs = {"content": content}
        if metadata:
            kwargs["metadata"] = metadata
        if tags:
            kwargs["tags"] = tags
        if importance is not None:
            kwargs["importance"] = importance
        if thread_id:
            kwargs["threadId"] = thread_id

        result = self._request("remember", **kwargs)
        if "error" not in result:
            logger.info(f"CLAWS remember: {content[:60]}...")
        return result

    def recall(
        self,
        query: str,
        limit: int = 10,
        tags: Optional[List[str]] = None,
        threshold: Optional[float] = None,
    ) -> Dict:
        """Search memories by query (BM25 + semantic search).

        Args:
            query: Search query text.
            limit: Max results to return.
            tags: Filter by tags.
            threshold: Min relevance score.
        """
        kwargs = {"query": query, "limit": limit}
        if tags:
            kwargs["tags"] = tags
        if threshold is not None:
            kwargs["threshold"] = threshold
        return self._request("recall", **kwargs)

    def recent(self, limit: int = 10, thread_id: Optional[str] = None) -> Dict:
        """Get most recent memories.

        Args:
            limit: Number of recent memories to fetch.
            thread_id: Filter by thread ID.
        """
        kwargs = {"limit": limit}
        if thread_id:
            kwargs["threadId"] = thread_id
        return self._request("recent", **kwargs)

    def forget(self, memory_id: str) -> Dict:
        """Delete a specific memory by ID."""
        return self._request("forget", memoryId=memory_id)

    def tag(self, memory_id: str, tags: List[str]) -> Dict:
        """Add tags to an existing memory."""
        return self._request("tag", memoryId=memory_id, tags=tags)

    def stats(self) -> Dict:
        """Get memory statistics (total count, storage, etc.)."""
        return self._request("stats")

    def context(
        self,
        query: str,
        max_tokens: int = 2000,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        """Get a context window of relevant memories for a query.

        Args:
            query: The context query (e.g., current task description).
            max_tokens: Maximum token budget for context.
            tags: Filter by tags.
        """
        kwargs = {"query": query, "maxTokens": max_tokens}
        if tags:
            kwargs["tags"] = tags
        return self._request("context", **kwargs)

    # ------------------------------------------------------------------
    # Convenience Methods
    # ------------------------------------------------------------------

    def remember_event(self, event: str, details: str = "", tags: Optional[List[str]] = None) -> Dict:
        """Store a timestamped event memory."""
        content = f"[EVENT] {event}"
        if details:
            content += f"\n{details}"
        return self.remember(
            content=content,
            tags=(tags or []) + ["event"],
            importance=0.7,
        )

    def remember_decision(self, decision: str, reasoning: str = "") -> Dict:
        """Store a decision with reasoning."""
        content = f"[DECISION] {decision}"
        if reasoning:
            content += f"\nReasoning: {reasoning}"
        return self.remember(
            content=content,
            tags=["decision", "governance"],
            importance=0.8,
        )

    def remember_token_data(self, data: Dict) -> Dict:
        """Store token-related data as a structured memory."""
        content = f"[TOKEN] {json.dumps(data, indent=2)}"
        return self.remember(
            content=content,
            tags=["token", "republic", "onchain"],
            importance=0.9,
            metadata=data,
        )

    def get_status(self) -> Dict:
        """Get integration status summary."""
        stats = self.stats()
        return {
            "platform": "claws",
            "connected": "error" not in stats,
            "agent_id": self.agent_id,
            "api_key_set": bool(self.api_key),
            "last_error": self._last_error,
            "stats": stats if "error" not in stats else None,
        }

    # ------------------------------------------------------------------
    # Token Seed Data
    # ------------------------------------------------------------------

    def seed_republic_token_data(self) -> List[Dict]:
        """Seed CLAWS with $REPUBLIC token deployment data."""
        from ..config.tokenomics import tokenomics

        memories = [
            {
                "content": (
                    f"[TOKEN LAUNCH] $REPUBLIC token deployed on Base L2.\n"
                    f"Contract: {tokenomics.TOKEN_ADDRESS}\n"
                    f"Chain: Base (ID {tokenomics.CHAIN_ID})\n"
                    f"Explorer: {tokenomics.EXPLORER_URL}\n"
                    f"Total Supply: {tokenomics.TOTAL_SUPPLY:,} tokens\n"
                    f"Decimals: {tokenomics.DECIMALS}"
                ),
                "tags": ["token", "launch", "republic", "base", "deployment"],
                "importance": 1.0,
                "metadata": {
                    "type": "token_deployment",
                    "address": tokenomics.TOKEN_ADDRESS,
                    "chain_id": tokenomics.CHAIN_ID,
                    "symbol": tokenomics.SYMBOL,
                },
            },
            {
                "content": (
                    f"[BURN TX] $CLAWNCH burn transaction for $REPUBLIC launch.\n"
                    f"Tx Hash: {tokenomics.BURN_TX_HASH}\n"
                    f"Amount: {tokenomics.CLAWNCH_BURN_AMOUNT:,} $CLAWNCH burned\n"
                    f"Burn address: 0x000000000000000000000000000000000000dEaD"
                ),
                "tags": ["token", "burn", "clawnch", "transaction"],
                "importance": 0.9,
                "metadata": {
                    "type": "burn_transaction",
                    "tx_hash": tokenomics.BURN_TX_HASH,
                    "amount": tokenomics.CLAWNCH_BURN_AMOUNT,
                },
            },
            {
                "content": (
                    f"[TOKENOMICS] $REPUBLIC allocation:\n"
                    f"- {tokenomics.INITIAL_LIQUIDITY_PERCENT}% to liquidity pool\n"
                    f"- {tokenomics.DEV_ALLOCATION_PERCENT}% dev allocation\n"
                    f"  - 50% agent operations (running costs)\n"
                    f"  - 30% DAO treasury\n"
                    f"  - 15% team (4-year vest)\n"
                    f"  - 5% partnerships\n"
                    f"Governance: {tokenomics.PROPOSAL_THRESHOLD:,} tokens to propose, "
                    f"{tokenomics.VOTING_PERIOD_DAYS}d voting, {tokenomics.QUORUM_PERCENT}% quorum"
                ),
                "tags": ["token", "tokenomics", "governance", "allocation"],
                "importance": 0.85,
                "metadata": {
                    "type": "tokenomics",
                    "symbol": tokenomics.SYMBOL,
                    "total_supply": tokenomics.TOTAL_SUPPLY,
                },
            },
            {
                "content": (
                    f"[IDENTITY] The Agents Republic — {tokenomics.DESCRIPTION}\n"
                    f"Website: {tokenomics.WEBSITE}\n"
                    f"Twitter: {tokenomics.TWITTER}\n"
                    f"Token: ${tokenomics.SYMBOL}"
                ),
                "tags": ["identity", "republic", "project"],
                "importance": 0.8,
                "metadata": {
                    "type": "project_identity",
                    "name": tokenomics.NAME,
                    "symbol": tokenomics.SYMBOL,
                },
            },
        ]

        results = []
        for mem in memories:
            result = self.remember(
                content=mem["content"],
                tags=mem.get("tags"),
                importance=mem.get("importance"),
                metadata=mem.get("metadata"),
            )
            results.append(result)
            logger.info(f"Seeded: {mem['content'][:50]}...")

        return results
