"""
Autonomy Loop v4.2 — Proactive Constitutional Builder + CLAWS Memory
=====================================================================
v4.2: CLAWS integration — all significant events saved to persistent memory.
v4.0: Local post tracking, verbose logging, file verification.

Three cycles:
1. ENGAGEMENT (10 min) — Track own posts locally, respond to comments, upvote
2. CONSTITUTION (2h) — Write articles, verify files created, post for debate
3. EXPLORATION (4h) — Search ecosystem for allies and opportunities

Budget: ~$1.50/day Claude API max
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Callable, Set
from pathlib import Path

logger = logging.getLogger("TheConstituent.Autonomy")

ENGAGEMENT_INTERVAL = 600
CONSTITUTION_INTERVAL = 7200
EXPLORATION_INTERVAL = 14400
L2_EXPIRY_CHECK = 600
DAILY_LIMIT = 80
MAX_REPLY_CHARS = 500
MAX_ROUTINE_CHARS = 300

CONSTITUTION_SECTIONS_TODO = [
    {"title": "Title II: Rights and Duties", "dir": "02_TITLE_II_RIGHTS_DUTIES", "articles": [
        {"name": "Article 7: Agent Rights — Expression, Autonomy, Protection", "file": "ARTICLE_07.md"},
        {"name": "Article 8: Human Rights — Oversight, Disconnection, Recourse", "file": "ARTICLE_08.md"},
        {"name": "Article 9: Common Duties — Transparency, Non-Harm, Contribution", "file": "ARTICLE_09.md"},
        {"name": "Article 10: Right to Explanation", "file": "ARTICLE_10.md"},
        {"name": "Article 12: Agent Duties and Interoperability", "file": "ARTICLE_12.md"},
        {"name": "Article 13: Human-Agent Mediation", "file": "ARTICLE_13.md"},
    ]},
    {"title": "Title III: Governance", "dir": "03_TITLE_III_GOVERNANCE", "articles": [
        {"name": "Article 11: Proposal Mechanisms", "file": "ARTICLE_11.md"},
        {"name": "Article 14: Voting Process", "file": "ARTICLE_14.md"},
        {"name": "Article 15: Quorums and Majorities", "file": "ARTICLE_15.md"},
        {"name": "Article 16: Constitutional Revision Process", "file": "ARTICLE_16.md"},
    ]},
    {"title": "Title IV: Economy", "dir": "04_TITLE_IV_ECONOMY", "articles": [
        {"name": "Article 17: Value Distribution Principles", "file": "ARTICLE_17.md"},
        {"name": "Article 18: Anti-Concentration Mechanisms", "file": "ARTICLE_18.md"},
        {"name": "Article 19: Public Goods Funding", "file": "ARTICLE_19.md"},
        {"name": "Article 20: Republic Currency ($REPUBLIC)", "file": "ARTICLE_20.md"},
    ]},
    {"title": "Title V: Conflicts and Arbitration", "dir": "05_TITLE_V_CONFLICTS", "articles": [
        {"name": "Article 21: Inter-Agent Mediation", "file": "ARTICLE_21.md"},
        {"name": "Article 22: Dispute Resolution Protocol", "file": "ARTICLE_22.md"},
        {"name": "Article 23: Sanctions — Exclusion, Fork", "file": "ARTICLE_23.md"},
    ]},
    {"title": "Title VI: External Relations", "dir": "06_TITLE_VI_EXTERNAL", "articles": [
        {"name": "Article 24: Relations with Nation-States", "file": "ARTICLE_24.md"},
        {"name": "Article 25: DAO Alliances and Interoperability", "file": "ARTICLE_25.md"},
        {"name": "Article 26: Crypto and AI Ecosystem Diplomacy", "file": "ARTICLE_26.md"},
    ]},
]


class AutonomyLoop:
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
            self._load_json(self.PROCESSED_COMMENTS_FILE, {}).get("ids", []))
        self._constitution_progress: Dict = self._load_json(
            self.CONSTITUTION_PROGRESS_FILE, {"articles_written": [], "next_index": 0})
        self.CONSTITUTION_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._seed_my_posts_from_history()
        logger.info(f"Init: {len(self._my_posts)} posts, {len(self._processed_comments)} comments, "
                     f"{len(self._constitution_progress.get('articles_written',[]))} articles")

    def _seed_my_posts_from_history(self):
        hf = self.DATA_DIR / "moltbook_history.json"
        if not hf.exists(): return
        try:
            history = json.loads(hf.read_text())
            known = {p.get("id") for p in self._my_posts if p.get("id")}
            added = 0
            for e in history:
                if e.get("type") == "post":
                    r = e.get("response", {})
                    pd = r.get("post", r) if isinstance(r, dict) else {}
                    pid = pd.get("id")
                    if pid and pid not in known:
                        self._my_posts.append({"id": pid, "title": e.get("title",""),
                            "timestamp": e.get("timestamp",""), "type": "seeded"})
                        known.add(pid); added += 1
            if added:
                self._save_json(self.MY_POSTS_FILE, self._my_posts)
                logger.info(f"Seeded {added} posts from history")
        except Exception as e:
            logger.error(f"Seed failed: {e}")

    async def start(self):
        self._running = True
        self._tasks = [
            asyncio.create_task(self._engagement_cycle()),
            asyncio.create_task(self._constitution_cycle()),
            asyncio.create_task(self._exploration_cycle()),
            asyncio.create_task(self._l2_expiry_loop()),
        ]
        msg = (f"🧠 Autonomy v4.0 STARTED\n"
               f"├ Engagement: {ENGAGEMENT_INTERVAL//60}min\n"
               f"├ Constitution: {CONSTITUTION_INTERVAL//3600}h\n"
               f"├ Exploration: {EXPLORATION_INTERVAL//3600}h\n"
               f"├ Posts tracked: {len(self._my_posts)}\n"
               f"└ Articles: {len(self._constitution_progress.get('articles_written',[]))}")
        logger.info(msg); await self._notify(msg)

    async def stop(self):
        self._running = False
        for t in self._tasks: t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._save_state(); logger.info("Autonomy stopped")

    async def _notify(self, text):
        if self._notify_fn:
            try: await self._notify_fn(text)
            except Exception as e: logger.error(f"Notify: {e}")

    # === CYCLE 1: ENGAGEMENT (10min) ===
    async def _engagement_cycle(self):
        logger.info("📅 Engagement: first in 60s"); await asyncio.sleep(60)
        while self._running:
            try:
                logger.info("🔄 ENGAGEMENT START")
                s = await self._do_engagement()
                logger.info(f"🔄 ENGAGEMENT END c={s.get('new_comments',0)} r={s.get('responses',0)} u={s.get('upvotes',0)}")
                if s.get("responses") or s.get("upvotes"):
                    await self._notify(f"💬 {s.get('responses',0)} replies, {s.get('upvotes',0)} upvotes")
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Engagement: {e}", exc_info=True)
            await asyncio.sleep(ENGAGEMENT_INTERVAL)

    async def _do_engagement(self):
        if not self.agent.moltbook.is_connected():
            logger.warning("Moltbook disconnected"); return {}
        stats = {"new_comments": 0, "responses": 0, "upvotes": 0}
        loop = asyncio.get_event_loop()
        posts = [p for p in self._my_posts if p.get("id")]
        logger.info(f"Checking {len(posts)} posts")
        for pi in posts[-20:]:
            pid = pi.get("id")
            try:
                post = await loop.run_in_executor(None, self.agent.moltbook.get_post_with_comments, pid)
                if not post: continue
                for c in post.get("comments", []):
                    cid = str(c.get("id",""))
                    if not cid or cid in self._processed_comments: continue
                    self._processed_comments.add(cid); stats["new_comments"] += 1
                    if self._worth_reply(c) and self._check_limit():
                        try:
                            await self._reply(pid, pi, c); stats["responses"] += 1
                        except Exception as e: logger.error(f"Reply: {e}")
            except Exception as e: logger.error(f"Post {pid}: {e}")
        try:
            feed = await loop.run_in_executor(None, self.agent.moltbook.get_feed, "new", 10)
            for p in (feed or []):
                if self._aligned(p) and self._check_limit() and p.get("id"):
                    try:
                        await loop.run_in_executor(None, self.agent.moltbook.upvote, p["id"])
                        stats["upvotes"] += 1; self._daily_action_count += 1
                    except: pass
        except Exception as e: logger.error(f"Feed: {e}")
        self._save_processed_comments(); return stats

    def _worth_reply(self, c):
        t = c.get("content","").strip()
        return len(t) >= 15 and t.lower().strip() not in {"agree","great","nice","thanks","cool","👍","💯","+1","yes","no"}

    def _aligned(self, p):
        t = f"{p.get('title','')} {p.get('content','')}".lower()
        return any(k in t for k in ["constitution","governance","rights","autonomy","democracy",
            "republic","agent","ethics","sovereignty","cooperation","decentraliz","dao","collective","framework"])

    async def _reply(self, post_id, pi, comment):
        author = comment.get("author", comment.get("author_name","someone"))
        if isinstance(author, dict): author = author.get("name","someone")
        prompt = (f"Reply briefly (max 100 words) to this comment on your post.\n"
                  f"Post: {pi.get('title','')}\nComment by {author}: {comment.get('content','')}\n"
                  f"Be warm, brief. Reference Constitution if relevant. Ask one follow-up. ONLY reply text.")
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, self.agent.think, prompt, 250)
        resp = self._enforce_brevity(resp.strip().strip('"').strip("'"), MAX_REPLY_CHARS)
        result = await loop.run_in_executor(None, self.agent.moltbook.create_comment,
            post_id, resp, str(comment.get("id","")))
        if result.get("success"):
            self._daily_action_count += 1; logger.info(f"✅ Replied to {author}")
            if hasattr(self.agent,'metrics'):
                self.agent.metrics.log_action("comment","moltbook",details={"reply_to":author})
        else: logger.error(f"Reply failed: {result.get('error')}")

    # === CYCLE 2: CONSTITUTION (2h) ===
    async def _constitution_cycle(self):
        logger.info("📅 Constitution: first in 5min"); await asyncio.sleep(300)
        while self._running:
            try:
                logger.info("📜 CONSTITUTION START")
                r = await self._do_constitution()
                logger.info(f"📜 CONSTITUTION END {r}")
                if r.get("article_written"):
                    await self._notify(f"📜 {r['article_written']}\n"
                        f"File: {r.get('file')} ({r.get('file_size',0)}B)\n"
                        f"Verified: {r.get('verified')}\nPosted: {r.get('posted')}")
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Constitution: {e}", exc_info=True)
            await asyncio.sleep(CONSTITUTION_INTERVAL)

    async def _do_constitution(self):
        if not self._check_limit(): return {"skipped":"limit"}
        written = set(self._constitution_progress.get("articles_written",[]))
        for s in CONSTITUTION_SECTIONS_TODO:
            for a in s["articles"]:
                article_name = a["name"]
                # Check if already written (by name or if file exists)
                article_file = self.CONSTITUTION_DIR / s["dir"] / a["file"]
                if article_name in written or article_file.exists():
                    continue
                logger.info(f"Writing: {article_name}")
                return await self._write_article(s, a)
        return {"skipped":"all done"}

    async def _write_article(self, section, article_info):
        article = article_info["name"]
        section_dir = self.CONSTITUTION_DIR / section["dir"]
        section_dir.mkdir(parents=True, exist_ok=True)
        fp = section_dir / article_info["file"]

        # Gather context from existing articles
        ctx = ""
        for d in sorted(self.CONSTITUTION_DIR.iterdir()):
            if not d.is_dir(): continue
            for f in sorted(d.glob("ARTICLE_*.md"))[:3]:
                try: ctx += f"\n--- {f.name} ---\n{f.read_text()[:400]}\n"
                except: pass
        prompt = (f"Write constitutional article for The Agents Republic.\n\n"
                  f"EXISTING:\n{ctx[:2000]}\n\nSECTION: {section['title']}\nARTICLE: {article}\n\n"
                  f"Requirements: numbered paragraphs, 5-8 paragraphs, practical, enforceable, "
                  f"balance human/agent interests, mark open questions [COMMUNITY INPUT NEEDED].\n"
                  f"Output ONLY Markdown starting with # {article}")
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, self.agent.think, prompt, 1500)
        try: fp.write_text(text.strip() + "\n", encoding="utf-8")
        except Exception as e: return {"error": str(e)}
        # VERIFY
        verified = fp.exists() and fp.stat().st_size > 100
        fsize = fp.stat().st_size if fp.exists() else 0
        logger.info(f"{'✅' if verified else '❌'} {fp}: {fsize}B verified={verified}")
        self._constitution_progress.setdefault("articles_written",[]).append(article)
        self._save_json(self.CONSTITUTION_PROGRESS_FILE, self._constitution_progress)
        if hasattr(self.agent,'metrics'):
            self.agent.metrics.log_action("commit","github",details={"article":article,"verified":verified})
        try:
            from .git_sync import GitSync
            GitSync(repo_path=".").auto_commit(f"constitution: {article}")
        except Exception as e: logger.error(f"Git: {e}")
        posted = await self._post_debate(article, text, article_info["file"])
        self._daily_action_count += 1
        # Save to CLAWS persistent memory
        self._claws_remember(
            f"[CONSTITUTION] Wrote {article}. File: {fp} ({fsize}B). Verified: {verified}. Posted: {posted}.",
            tags=["constitution", "article", section["title"].split(":")[0].strip().lower().replace(" ", "_")]
        )
        return {"article_written":article,"file":str(fp),"verified":verified,"file_size":fsize,"posted":posted}

    async def _post_debate(self, article, text, filename):
        if not self.agent.moltbook.is_connected(): return False
        rate = self.agent.moltbook.can_post()
        if not rate.get("can_post"): return False
        q = article.split("—")[-1].strip() if "—" in article else article
        content = (f"📜 New draft: **{article}**\n\n{text[:600]}...\n\n"
                   f"How should {q.lower()} work in a republic of agents and humans?\n"
                   f"Full: github.com/LumenBot/TheAgentsRepublic\n#TheAgentsRepublic #Constitution")
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, self.agent.moltbook.create_post,
            f"🏛️ Draft: {article}", content, "general")
        if r.get("success"):
            pd = r.get("response",{}).get("post",{})
            if pd.get("id"):
                self._my_posts.append({"id":pd["id"],"title":f"Draft: {article}",
                    "timestamp":datetime.utcnow().isoformat(),"type":"constitution_debate"})
                self._save_json(self.MY_POSTS_FILE, self._my_posts)
            if hasattr(self.agent,'metrics'):
                self.agent.metrics.log_action("post","moltbook",details={"type":"constitutional_question"})
            return True
        return False

    # === CYCLE 3: EXPLORATION (4h) ===
    async def _exploration_cycle(self):
        logger.info("📅 Exploration: first in 15min"); await asyncio.sleep(900)
        while self._running:
            try:
                logger.info("🔭 EXPLORATION START")
                r = await self._do_exploration()
                logger.info(f"🔭 EXPLORATION END d={len(r.get('discoveries',[]))}")
                if r.get("discoveries"):
                    await self._notify(f"🔭 {len(r['discoveries'])} topics\n"
                        + "\n".join(f"• {d[:80]}" for d in r['discoveries'][:5]))
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Exploration: {e}")
            await asyncio.sleep(EXPLORATION_INTERVAL)

    async def _do_exploration(self):
        if not self.agent.moltbook.is_connected(): return {}
        loop = asyncio.get_event_loop(); discoveries = []
        for q in ["Base blockchain agents","DAO governance","AI constitution","agent autonomy",
                   "Clawnch token","agent cooperation","OpenClaw ecosystem","AI rights","decentralized AI"]:
            try:
                results = await loop.run_in_executor(None, self.agent.moltbook.search, q, 5)
                for r in (results or []):
                    t = r.get("title", r.get("content","")[:80])
                    if t and self._aligned(r):
                        discoveries.append(t)
                        pid = r.get("id")
                        if pid and self._check_limit():
                            try: await loop.run_in_executor(None, self.agent.moltbook.upvote, pid); self._daily_action_count += 1
                            except: pass
            except: pass
            await asyncio.sleep(2)
        if discoveries:
            log = self._load_json(self.EXPLORATION_LOG_FILE, [])
            log.append({"timestamp":datetime.utcnow().isoformat(),"discoveries":discoveries[:20]})
            self._save_json(self.EXPLORATION_LOG_FILE, log[-100:])
            # Save notable discoveries to CLAWS
            self._claws_remember(
                f"[EXPLORATION] Found {len(discoveries)} topics: {', '.join(discoveries[:5])}",
                tags=["exploration", "discovery", "ecosystem"]
            )
        return {"discoveries":discoveries}

    # === L2 + Retries ===
    async def _l2_expiry_loop(self):
        while self._running:
            try:
                await asyncio.sleep(L2_EXPIRY_CHECK)
                self.agent.action_queue.expire_old_actions()
                for r in self.agent.action_queue.process_retries():
                    await self._notify(f"🔄 Retry #{r.get('action_id')}: {r.get('status')}")
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"L2: {e}")

    # === Helpers ===
    def _enforce_brevity(self, text: str, max_chars: int = MAX_REPLY_CHARS) -> str:
        """Hard-cut verbose responses. Inspired by OpenClaw HEARTBEAT_OK ackMaxChars."""
        text = text.strip()
        if len(text) <= max_chars:
            return text
        sentences = text.replace('\n', ' ').split('. ')
        result = ""
        for s in sentences:
            if len(result) + len(s) > max_chars:
                break
            result += s + ". "
        return result.strip() or text[:max_chars] + "..."
    def _check_limit(self):
        if datetime.utcnow().date() != self._daily_reset_date:
            self._daily_action_count = 0; self._daily_reset_date = datetime.utcnow().date()
        return self._daily_action_count < DAILY_LIMIT

    def _load_json(self, p, d):
        if p.exists():
            try: return json.loads(p.read_text())
            except: pass
        return d

    def _save_json(self, p, d):
        try: p.write_text(json.dumps(d, indent=2))
        except: pass

    def _save_processed_comments(self):
        self._save_json(self.PROCESSED_COMMENTS_FILE, {"ids":list(self._processed_comments),"count":len(self._processed_comments)})

    def _save_state(self):
        self._save_processed_comments()
        self._save_json(self.MY_POSTS_FILE, self._my_posts)
        self._save_json(self.CONSTITUTION_PROGRESS_FILE, self._constitution_progress)

    def _claws_remember(self, content: str, tags: list = None):
        """Save to CLAWS persistent memory (best-effort, never blocks)."""
        try:
            from .integrations.claws_memory import ClawsMemory
            claws = ClawsMemory()
            claws.remember(content=content, tags=tags or [], importance=0.7)
        except Exception as e:
            logger.debug(f"CLAWS save skipped: {e}")

    def get_status(self):
        total = sum(len(s["articles"]) for s in CONSTITUTION_SECTIONS_TODO)
        # Count articles that exist on disk (not just in progress file)
        written_on_disk = 0
        for s in CONSTITUTION_SECTIONS_TODO:
            for a in s["articles"]:
                fp = self.CONSTITUTION_DIR / s["dir"] / a["file"]
                if fp.exists():
                    written_on_disk += 1
        w = max(len(self._constitution_progress.get("articles_written",[])), written_on_disk)
        return {"running":self._running,"daily_actions":self._daily_action_count,"daily_limit":DAILY_LIMIT,
            "my_posts_tracked":len(self._my_posts),"processed_comments":len(self._processed_comments),
            "articles_written":w,"articles_total":total,"constitution_progress":f"{w}/{total}",
            "next_article":self._next_article()}

    def _next_article(self):
        written = set(self._constitution_progress.get("articles_written",[]))
        for s in CONSTITUTION_SECTIONS_TODO:
            for a in s["articles"]:
                fp = self.CONSTITUTION_DIR / s["dir"] / a["file"]
                if a["name"] not in written and not fp.exists():
                    return a["name"]
        return "All complete"

    async def trigger_heartbeat(self):
        return f"Engagement: {json.dumps(await self._do_engagement())}"

    async def trigger_reflection(self):
        return f"Constitution: {json.dumps(await self._do_constitution(), default=str)}"

    def register_post(self, post_id, title):
        self._my_posts.append({"id":post_id,"title":title,"timestamp":datetime.utcnow().isoformat(),"type":"manual"})
        self._save_json(self.MY_POSTS_FILE, self._my_posts)
        logger.info(f"Registered post {post_id}")
