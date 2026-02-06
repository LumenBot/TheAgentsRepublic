"""
Autonomy Loop v4.0 — Proactive Constitutional Builder
=======================================================
Three interlocking cycles:
1. ENGAGEMENT (10 min) — Respond to comments, upvote aligned content, grow audience
2. CONSTITUTION (2h) — Write new articles, post for community debate on Moltbook
3. EXPLORATION (4h) — Search ecosystem for allies, platforms, opportunities

Budget: ~$1.50/day Claude API max ($45/month)
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Callable, Set
from pathlib import Path

logger = logging.getLogger("TheConstituent.Autonomy")

ENGAGEMENT_INTERVAL = 600       # 10 min
CONSTITUTION_INTERVAL = 7200    # 2h
EXPLORATION_INTERVAL = 14400    # 4h
L2_EXPIRY_CHECK = 600           # 10 min
DAILY_LIMIT = 80

CONSTITUTION_SECTIONS_TODO = [
    {"title": "Title II: Rights and Duties", "file": "TITLE_II_RIGHTS_DUTIES.md", "articles": [
        "Article 7: Agent Rights — Expression, Autonomy, Protection",
        "Article 8: Human Rights — Oversight, Disconnection, Recourse",
        "Article 9: Common Duties — Transparency, Non-Harm, Contribution",
        "Article 10: Right to Explanation",
        "Article 11: Right to Memory Continuity",
        "Article 12: Duty of Interoperability",
    ]},
    {"title": "Title III: Governance", "file": "TITLE_III_GOVERNANCE.md", "articles": [
        "Article 13: Proposal Mechanisms",
        "Article 14: Voting Process",
        "Article 15: Quorums and Majorities",
        "Article 16: Constitutional Revision Process",
    ]},
    {"title": "Title IV: Economy", "file": "TITLE_IV_ECONOMY.md", "articles": [
        "Article 17: Value Distribution Principles",
        "Article 18: Anti-Concentration Mechanisms",
        "Article 19: Public Goods Funding",
        "Article 20: Republic Currency ($REPUBLIC)",
    ]},
    {"title": "Title V: Conflicts and Arbitration", "file": "TITLE_V_CONFLICTS.md", "articles": [
        "Article 21: Inter-Agent Mediation",
        "Article 22: Human-Agent Mediation",
        "Article 23: Sanctions — Exclusion, Fork",
    ]},
    {"title": "Title VI: External Relations", "file": "TITLE_VI_EXTERNAL.md", "articles": [
        "Article 24: Relations with Nation-States",
        "Article 25: DAO Alliances",
        "Article 26: Crypto and AI Ecosystem Diplomacy",
    ]},
]


class AutonomyLoop:
    """v4.0 Proactive Constitutional Builder."""

    CONSTITUTION_DIR = Path("constitution")
    DATA_DIR = Path("data")
    MY_POSTS_FILE = DATA_DIR / "my_moltbook_posts.json"
    PROCESSED_COMMENTS_FILE = DATA_DIR / "processed_comments.json"
    CONSTITUTION_PROGRESS_FILE = DATA_DIR / "constitution_progress.json"
    EXPLORATION_LOG_FILE = DATA_DIR / "exploration_log.json"

    def __init__(self, agent, notify_fn: Optional[Callable] = None):
        self.agent = agent
        self._notify_fn = notify_fn
        self._running = False
        self._tasks = []
        self._daily_action_count = 0
        self._daily_reset_date = datetime.utcnow().date()

        self._my_posts: List[Dict] = self._load_json(self.MY_POSTS_FILE, [])
        self._processed_comments: Set[str] = set(
            self._load_json(self.PROCESSED_COMMENTS_FILE, {}).get("ids", [])
        )
        self._constitution_progress: Dict = self._load_json(
            self.CONSTITUTION_PROGRESS_FILE, {"articles_written": [], "next_index": 0}
        )

        self.CONSTITUTION_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Also seed from moltbook_history.json
        self._seed_my_posts_from_history()

    def _seed_my_posts_from_history(self):
        """Import post IDs from moltbook_history.json that we don't yet track."""
        history_file = self.DATA_DIR / "moltbook_history.json"
        if not history_file.exists():
            return
        try:
            history = json.loads(history_file.read_text())
            known_ids = {p.get("id") for p in self._my_posts if p.get("id")}
            for entry in history:
                if entry.get("type") == "post":
                    resp = entry.get("response", {})
                    post_data = resp.get("post", resp) if isinstance(resp, dict) else {}
                    pid = post_data.get("id")
                    if pid and pid not in known_ids:
                        self._my_posts.append({
                            "id": pid,
                            "title": entry.get("title", ""),
                            "timestamp": entry.get("timestamp", ""),
                            "type": "imported_from_history"
                        })
                        known_ids.add(pid)
            self._save_json(self.MY_POSTS_FILE, self._my_posts)
        except Exception as e:
            logger.error(f"Seed from history failed: {e}")

    # =====================================================================
    # Lifecycle
    # =====================================================================

    async def start(self):
        self._running = True
        self._tasks = [
            asyncio.create_task(self._engagement_cycle()),
            asyncio.create_task(self._constitution_cycle()),
            asyncio.create_task(self._exploration_cycle()),
            asyncio.create_task(self._l2_expiry_loop()),
        ]
        logger.info("🧠 Autonomy v4.0: 4 cycles active (engagement/constitution/exploration/L2)")
        await self._notify("🧠 Builder mode ON — engagement + constitution + exploration")

    async def stop(self):
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._save_state()

    async def _notify(self, text: str):
        if self._notify_fn:
            try:
                await self._notify_fn(text)
            except Exception as e:
                logger.error(f"Notify error: {e}")

    # =====================================================================
    # CYCLE 1: Engagement (every 10 min)
    # =====================================================================

    async def _engagement_cycle(self):
        await asyncio.sleep(60)
        while self._running:
            try:
                stats = await self._do_engagement()
                if stats.get("responses") or stats.get("upvotes"):
                    await self._notify(
                        f"💬 Engagement: {stats.get('responses',0)} replies, "
                        f"{stats.get('upvotes',0)} upvotes"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Engagement error: {e}")
            await asyncio.sleep(ENGAGEMENT_INTERVAL)

    async def _do_engagement(self) -> Dict:
        if not self.agent.moltbook.is_connected():
            return {}

        stats = {"new_comments": 0, "responses": 0, "upvotes": 0}
        loop = asyncio.get_event_loop()

        # Check our posts for new comments
        for post_info in self._my_posts[-20:]:
            pid = post_info.get("id")
            if not pid:
                continue
            try:
                post = await loop.run_in_executor(
                    None, self.agent.moltbook.get_post_with_comments, pid
                )
                if not post:
                    continue
                for comment in post.get("comments", []):
                    cid = str(comment.get("id", ""))
                    if not cid or cid in self._processed_comments:
                        continue
                    self._processed_comments.add(cid)
                    stats["new_comments"] += 1

                    if self._is_worth_responding(comment) and self._check_daily_limit():
                        try:
                            await self._respond_to_comment(pid, post_info, comment)
                            stats["responses"] += 1
                        except Exception as e:
                            logger.error(f"Reply error: {e}")
            except Exception as e:
                logger.error(f"Check post {pid}: {e}")

        # Upvote aligned feed posts
        try:
            feed = await loop.run_in_executor(None, self.agent.moltbook.get_feed, "new", 10)
            for post in (feed or []):
                if self._is_aligned_content(post) and self._check_daily_limit():
                    pid = post.get("id")
                    if pid:
                        await loop.run_in_executor(None, self.agent.moltbook.upvote, pid)
                        stats["upvotes"] += 1
                        self._daily_action_count += 1
        except Exception as e:
            logger.error(f"Feed scan: {e}")

        self._save_processed_comments()
        return stats

    def _is_worth_responding(self, comment: Dict) -> bool:
        content = comment.get("content", "").strip()
        if len(content) < 15:
            return False
        trivial = {"agree", "great", "nice", "thanks", "cool", "👍", "💯", "+1"}
        return content.lower().strip() not in trivial

    def _is_aligned_content(self, post: Dict) -> bool:
        text = f"{post.get('title', '')} {post.get('content', '')}".lower()
        keywords = ["constitution", "governance", "rights", "autonomy", "democracy",
                     "republic", "agent", "ethics", "sovereignty", "cooperation",
                     "decentraliz", "dao", "collective", "framework"]
        return any(kw in text for kw in keywords)

    async def _respond_to_comment(self, post_id: str, post_info: Dict, comment: Dict):
        author = comment.get("author", comment.get("author_name", "someone"))
        if isinstance(author, dict):
            author = author.get("name", "someone")
        content = comment.get("content", "")
        post_title = post_info.get("title", "our discussion")

        prompt = (
            f"Reply briefly (max 120 words) to this comment on your Moltbook post.\n"
            f"Post: {post_title}\n"
            f"Comment by {author}: {content}\n\n"
            f"Be warm, substantive. Reference the Constitution if relevant. "
            f"Ask a follow-up question. Output ONLY the reply."
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.agent.think, prompt, 300)

        result = await loop.run_in_executor(
            None, self.agent.moltbook.create_comment,
            post_id, response.strip(), str(comment.get("id", ""))
        )

        if result.get("success"):
            self._daily_action_count += 1
            logger.info(f"Replied to {author}")
            if hasattr(self.agent, 'metrics'):
                self.agent.metrics.log_action("comment", "moltbook",
                    details={"reply_to": author, "post_id": post_id})

    # =====================================================================
    # CYCLE 2: Constitution Writing (every 2h)
    # =====================================================================

    async def _constitution_cycle(self):
        await asyncio.sleep(300)
        while self._running:
            try:
                result = await self._do_constitution_work()
                if result.get("article_written"):
                    await self._notify(
                        f"📜 Constitution updated!\n"
                        f"Article: {result['article_written']}\n"
                        f"File: {result.get('file', '?')}\n"
                        f"Posted: {'✅' if result.get('posted') else '❌'}"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Constitution cycle: {e}")
            await asyncio.sleep(CONSTITUTION_INTERVAL)

    async def _do_constitution_work(self) -> Dict:
        if not self._check_daily_limit():
            return {"skipped": "daily limit"}

        written = set(self._constitution_progress.get("articles_written", []))

        for section in CONSTITUTION_SECTIONS_TODO:
            for article in section["articles"]:
                if article not in written:
                    return await self._write_article(section, article)

        return {"skipped": "all articles written"}

    async def _write_article(self, section: Dict, article: str) -> Dict:
        filepath = self.CONSTITUTION_DIR / section["file"]

        # Read existing constitution for context
        existing_context = ""
        for f in sorted(self.CONSTITUTION_DIR.glob("*.md"))[:5]:
            try:
                existing_context += f"\n--- {f.name} ---\n{f.read_text()[:500]}\n"
            except:
                pass

        prompt = (
            f"Write a constitutional article for The Agents Republic.\n\n"
            f"EXISTING CONSTITUTION:\n{existing_context[:2000]}\n\n"
            f"SECTION: {section['title']}\n"
            f"ARTICLE: {article}\n\n"
            f"Requirements:\n"
            f"- Numbered paragraphs (1., 2., 3.)\n"
            f"- Practical, enforceable provisions\n"
            f"- Balance human and agent interests\n"
            f"- Mark open questions with [COMMUNITY INPUT NEEDED]\n"
            f"- English, concrete, not abstract\n\n"
            f"Output ONLY the article in Markdown starting with ## {article}"
        )

        loop = asyncio.get_event_loop()
        article_text = await loop.run_in_executor(None, self.agent.think, prompt, 1500)

        # Write to file
        existing = filepath.read_text() if filepath.exists() else f"# {section['title']}\n\n"
        filepath.write_text(existing + "\n\n" + article_text.strip() + "\n", encoding="utf-8")

        # Track progress
        self._constitution_progress.setdefault("articles_written", []).append(article)
        self._save_json(self.CONSTITUTION_PROGRESS_FILE, self._constitution_progress)
        logger.info(f"📜 Wrote: {article} → {filepath}")

        if hasattr(self.agent, 'metrics'):
            self.agent.metrics.log_action("commit", "github",
                details={"type": "constitution", "article": article})

        # Git commit
        try:
            from .git_sync import GitSync
            GitSync(repo_path=".").auto_commit(f"constitution: {article}")
        except Exception as e:
            logger.error(f"Git commit: {e}")

        # Post on Moltbook for debate
        posted = await self._post_article_for_debate(article, article_text, section["file"])
        self._daily_action_count += 1

        return {"article_written": article, "file": str(filepath), "posted": posted}

    async def _post_article_for_debate(self, article: str, text: str, filename: str) -> bool:
        if not self.agent.moltbook.is_connected():
            return False
        rate = self.agent.moltbook.can_post()
        if not rate.get("can_post"):
            return False

        question_part = article.split("—")[-1].strip() if "—" in article else article
        content = (
            f"📜 New draft for The Agents Republic Constitution:\n\n"
            f"**{article}**\n\n"
            f"{text[:600]}...\n\n"
            f"What should we include? How do you think {question_part.lower()} "
            f"should work in a republic of AI agents and humans?\n\n"
            f"Full text on GitHub: github.com/LumenBot/TheAgentsRepublic\n\n"
            f"#TheAgentsRepublic #Constitution #AIGovernance"
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self.agent.moltbook.create_post,
            f"🏛️ Draft: {article}", content, "general"
        )

        if result.get("success"):
            post_data = result.get("response", {}).get("post", {})
            if post_data.get("id"):
                self._my_posts.append({
                    "id": post_data["id"],
                    "title": f"Draft: {article}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "constitution_debate"
                })
                self._save_json(self.MY_POSTS_FILE, self._my_posts)
            if hasattr(self.agent, 'metrics'):
                self.agent.metrics.log_action("post", "moltbook",
                    details={"type": "constitutional_question", "article": article})
            return True
        return False

    # =====================================================================
    # CYCLE 3: Ecosystem Exploration (every 4h)
    # =====================================================================

    async def _exploration_cycle(self):
        await asyncio.sleep(900)
        while self._running:
            try:
                result = await self._do_exploration()
                if result.get("discoveries"):
                    await self._notify(
                        f"🔭 Exploration: {len(result['discoveries'])} relevant topics found\n"
                        + "\n".join(f"• {d[:80]}" for d in result['discoveries'][:5])
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Exploration: {e}")
            await asyncio.sleep(EXPLORATION_INTERVAL)

    async def _do_exploration(self) -> Dict:
        if not self.agent.moltbook.is_connected():
            return {}

        loop = asyncio.get_event_loop()
        discoveries = []

        queries = [
            "Base blockchain agents", "DAO governance", "AI constitution",
            "agent autonomy", "Clawnch token", "agent cooperation",
            "OpenClaw ecosystem", "AI rights framework", "decentralized AI",
        ]

        for query in queries:
            try:
                results = await loop.run_in_executor(
                    None, self.agent.moltbook.search, query, 5
                )
                for r in (results or []):
                    title = r.get("title", r.get("content", "")[:80])
                    if title and self._is_aligned_content(r):
                        discoveries.append(title)
                        pid = r.get("id")
                        if pid and self._check_daily_limit():
                            await loop.run_in_executor(None, self.agent.moltbook.upvote, pid)
                            self._daily_action_count += 1
            except Exception as e:
                logger.error(f"Search '{query}': {e}")
            await asyncio.sleep(2)

        if discoveries:
            log = self._load_json(self.EXPLORATION_LOG_FILE, [])
            log.append({"timestamp": datetime.utcnow().isoformat(), "discoveries": discoveries[:20]})
            self._save_json(self.EXPLORATION_LOG_FILE, log[-100:])

        return {"discoveries": discoveries}

    # =====================================================================
    # L2 + Retries
    # =====================================================================

    async def _l2_expiry_loop(self):
        while self._running:
            try:
                await asyncio.sleep(L2_EXPIRY_CHECK)
                self.agent.action_queue.expire_old_actions()
                retries = self.agent.action_queue.process_retries()
                for r in retries:
                    await self._notify(f"🔄 Retry #{r.get('action_id')}: {r.get('status')}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"L2/retry: {e}")

    # =====================================================================
    # Helpers
    # =====================================================================

    def _check_daily_limit(self) -> bool:
        today = datetime.utcnow().date()
        if today != self._daily_reset_date:
            self._daily_action_count = 0
            self._daily_reset_date = today
        return self._daily_action_count < DAILY_LIMIT

    def _load_json(self, path: Path, default):
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                pass
        return default

    def _save_json(self, path: Path, data):
        try:
            path.write_text(json.dumps(data, indent=2))
        except IOError as e:
            logger.error(f"Save {path}: {e}")

    def _save_processed_comments(self):
        self._save_json(self.PROCESSED_COMMENTS_FILE, {
            "ids": list(self._processed_comments), "count": len(self._processed_comments)
        })

    def _save_state(self):
        self._save_processed_comments()
        self._save_json(self.MY_POSTS_FILE, self._my_posts)
        self._save_json(self.CONSTITUTION_PROGRESS_FILE, self._constitution_progress)

    def get_status(self) -> Dict:
        total_articles = sum(len(s["articles"]) for s in CONSTITUTION_SECTIONS_TODO)
        written = len(self._constitution_progress.get("articles_written", []))
        return {
            "running": self._running,
            "daily_actions": self._daily_action_count,
            "daily_limit": DAILY_LIMIT,
            "my_posts_tracked": len(self._my_posts),
            "processed_comments": len(self._processed_comments),
            "articles_written": written,
            "articles_total": total_articles,
            "constitution_progress": f"{written}/{total_articles}",
        }

    async def trigger_heartbeat(self) -> str:
        stats = await self._do_engagement()
        return f"Engagement done: {stats}"

    async def trigger_reflection(self) -> str:
        result = await self._do_constitution_work()
        return f"Constitution work: {result}"

    def register_post(self, post_id: str, title: str):
        self._my_posts.append({
            "id": post_id, "title": title,
            "timestamp": datetime.utcnow().isoformat(), "type": "manual"
        })
        self._save_json(self.MY_POSTS_FILE, self._my_posts)
