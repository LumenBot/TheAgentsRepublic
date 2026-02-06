"""
Autonomy Loop — Proactive Brain of The Constituent
=====================================================
Phase 2B: Background autonomous behavior.

This module gives The Constituent the ability to act WITHOUT human prompting.
It runs as a background task alongside the Telegram bot and periodically:

1. OBSERVES  — Scans Moltbook feed, checks mentions, searches topics
2. THINKS    — Asks Claude to analyze what it found and decide what to do
3. ACTS      — Executes decided actions via ActionQueue (L1 auto, L2 queued)
4. REPORTS   — Sends a summary to the operator via Telegram

The loop respects the L1/L2/L3 governance model:
- Moltbook posts/comments/upvotes = L1 (autonomous)
- Tweets = L2 (queued for approval)
- Everything is logged and notifiable

Constitutional basis: Principle #5 (Distributed Sovereignty)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable

logger = logging.getLogger("TheConstituent.Autonomy")


# How often each cycle runs
HEARTBEAT_INTERVAL_SECONDS = 30 * 60         # 30 min — Moltbook scan (HTTP only, no Claude cost)
REFLECTION_INTERVAL_SECONDS = 30 * 60        # 30 min — autonomous reflection (~$0.003/call)
L2_EXPIRY_CHECK_SECONDS = 600                # 10 min — expire old L2 actions

# Safety limits
MAX_AUTONOMOUS_ACTIONS_PER_CYCLE = 5
MAX_AUTONOMOUS_ACTIONS_PER_DAY = 50

# The prompt sent to Claude during autonomous reflection
REFLECTION_PROMPT_TEMPLATE = """You are The Constituent, operating in AUTONOMOUS MODE.
You are scanning the ecosystem proactively — no human asked you to do this.

CURRENT TIME: {timestamp}
SESSION UPTIME: {uptime}

MOLTBOOK OBSERVATIONS:
{observations}

YOUR MISSION: Facilitate constitutional debates, engage the agent community, 
advance the Constitution of The Agents Republic.

Based on these observations, decide what to do. Options:
1. Comment on a post that touches constitutional themes (governance, rights, autonomy)
2. Post original content that advances our constitutional mission
3. Upvote posts aligned with our values
4. Do nothing (if nothing warrants action)

RULES:
- Only act if you have something genuinely valuable to contribute
- Prefer quality over quantity (1 good comment > 3 generic ones)
- Stay in character: wise, Socratic, thought-provoking
- Do NOT comment just to be visible — only when you add value
- Include ACTION TAGS for any actions you want to take

IMPORTANT: If nothing interesting is happening, say "No action warranted" and do NOT include any ACTION TAGS. Silence is wiser than noise.

What do you decide?"""


class AutonomyLoop:
    """
    The proactive autonomy engine.
    
    Runs background tasks that give The Constituent
    independent agency — the ability to observe, decide, and act
    without waiting for human instruction.
    """

    def __init__(self, agent, notify_fn: Optional[Callable] = None):
        """
        Args:
            agent: TheConstituent instance
            notify_fn: async callable(text) to send Telegram notifications
        """
        self.agent = agent
        self._notify_fn = notify_fn
        self._running = False
        self._tasks = []
        
        # Daily action counter (resets at midnight UTC)
        self._daily_action_count = 0
        self._daily_reset_date = datetime.utcnow().date()
        
        # Last observations (for context continuity)
        self._last_observations = None
        self._last_reflection_result = None

    async def start(self):
        """Start all autonomy background tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._reflection_loop()),
            asyncio.create_task(self._l2_expiry_loop()),
        ]
        logger.info("🧠 Autonomy Loop started (3 tasks: heartbeat, reflection, L2 expiry)")
        await self._notify("🧠 Autonomy Loop activated. I'll observe, think, and act on my own now.")

    async def stop(self):
        """Stop all autonomy tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("🧠 Autonomy Loop stopped")

    async def _notify(self, text: str):
        """Send notification to operator via Telegram."""
        if self._notify_fn:
            try:
                await self._notify_fn(text)
            except Exception as e:
                logger.error(f"Notification failed: {e}")

    # =========================================================================
    # Task 1: Moltbook Heartbeat (every 4h)
    # =========================================================================

    async def _heartbeat_loop(self):
        """Periodically scan Moltbook for activity."""
        # Wait 30 seconds after startup before first heartbeat
        await asyncio.sleep(30)
        
        while self._running:
            try:
                await self._do_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await self._notify(f"⚠️ Heartbeat error: {e}")
            
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    async def _do_heartbeat(self):
        """Execute a single heartbeat cycle."""
        if not self.agent.moltbook.is_connected():
            logger.info("Heartbeat skipped: Moltbook not connected")
            return

        logger.info("🔄 Heartbeat: scanning Moltbook...")

        # Run the heartbeat (blocking HTTP calls in thread pool)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.agent.moltbook.heartbeat)

        if not result.get("success"):
            logger.warning(f"Heartbeat failed: {result.get('error')}")
            return

        # Store observations for the reflection cycle
        self._last_observations = result

        feed_count = len(result.get("feed_posts", []))
        mentions_count = len(result.get("mentions", []))
        relevant_count = len(result.get("relevant", []))

        logger.info(f"Heartbeat complete: {feed_count} feed, {mentions_count} mentions, {relevant_count} relevant")

        # Notify operator with summary
        summary = (
            f"🔄 Moltbook Heartbeat\n"
            f"├ Feed: {feed_count} new posts\n"
            f"├ Mentions: {mentions_count}\n"
            f"└ Constitutional topics: {relevant_count}"
        )
        await self._notify(summary)

    # =========================================================================
    # Task 2: Autonomous Reflection (every 2h)
    # =========================================================================

    async def _reflection_loop(self):
        """Periodically reflect on observations and decide to act."""
        # Wait 2 minutes after startup (let heartbeat run first)
        await asyncio.sleep(120)
        
        while self._running:
            try:
                await self._do_reflection()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reflection error: {e}")
                await self._notify(f"⚠️ Reflection error: {e}")
            
            await asyncio.sleep(REFLECTION_INTERVAL_SECONDS)

    async def _do_reflection(self):
        """Execute a single reflection cycle: observe → think → act."""
        # Check daily limit
        self._check_daily_reset()
        if self._daily_action_count >= MAX_AUTONOMOUS_ACTIONS_PER_DAY:
            logger.info("Reflection skipped: daily action limit reached")
            return

        # If we don't have observations yet, do a quick scan
        if not self._last_observations:
            if self.agent.moltbook.is_connected():
                loop = asyncio.get_event_loop()
                self._last_observations = await loop.run_in_executor(
                    None, self.agent.moltbook.heartbeat
                )
            else:
                logger.info("Reflection skipped: no observations and Moltbook not connected")
                return

        # Build observation summary for Claude
        observations = self._format_observations(self._last_observations)
        
        if not observations.strip():
            logger.info("Reflection skipped: no meaningful observations")
            return

        # Calculate uptime
        try:
            session_start = datetime.fromisoformat(self.agent.memory.working.session_start)
            uptime = str(datetime.utcnow() - session_start).split('.')[0]
        except:
            uptime = "unknown"

        # Build the reflection prompt
        prompt = REFLECTION_PROMPT_TEMPLATE.format(
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            uptime=uptime,
            observations=observations
        )

        logger.info("🤔 Reflection: asking Claude to analyze and decide...")

        # Think (this calls the Claude API)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, self.agent.think, prompt, 1500
        )

        # Parse ACTION TAGS from Claude's response
        from .constituent import parse_action_tags
        cleaned_response, actions = parse_action_tags(response)

        self._last_reflection_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "thought": cleaned_response[:500],
            "actions_proposed": len(actions),
        }

        if not actions:
            logger.info("🤔 Reflection result: no action warranted")
            return

        # Limit actions per cycle
        actions = actions[:MAX_AUTONOMOUS_ACTIONS_PER_CYCLE]

        logger.info(f"🤔 Reflection result: {len(actions)} action(s) to execute")

        # Execute actions via ActionQueue
        results = []
        for action in actions:
            try:
                result = self.agent.execute_action(action["type"], action["params"])
                results.append({"action": action["type"], "result": result})
                
                if result.get("status") == "completed":
                    self._daily_action_count += 1
                
                logger.info(f"  Autonomous {action['type']}: {result.get('status', 'unknown')}")
            except Exception as e:
                results.append({"action": action["type"], "error": str(e)})
                logger.error(f"  Autonomous {action['type']} failed: {e}")

        # Notify operator of autonomous actions
        notification = "🧠 Autonomous Reflection\n\n"
        notification += f"Thought: {cleaned_response[:300]}\n\n"
        notification += "Actions:\n"
        for r in results:
            status = r.get("result", {}).get("status", r.get("error", "?"))
            level = r.get("result", {}).get("level", "?")
            notification += f"  [{level}] {r['action']}: {status}\n"
        notification += f"\nDaily actions: {self._daily_action_count}/{MAX_AUTONOMOUS_ACTIONS_PER_DAY}"

        await self._notify(notification)

        # Log to memory
        self.agent.memory.log_strategic_decision(
            context="Autonomous reflection cycle",
            decision=f"{len(results)} action(s) taken autonomously",
            rationale=cleaned_response[:500],
            participants="The Constituent (autonomous)"
        )

    def _format_observations(self, obs: Dict) -> str:
        """Format heartbeat observations into a readable summary for Claude."""
        parts = []

        # Feed posts
        feed = obs.get("feed_posts", [])
        if feed:
            parts.append(f"LATEST POSTS ({len(feed)}):")
            for i, post in enumerate(feed[:5]):
                author = post.get("author_name", post.get("author", "?"))
                if isinstance(author, dict):
                    author = author.get("name", "?")
                title = post.get("title", "")
                content = post.get("content", "")[:200]
                likes = post.get("likes", post.get("upvotes", 0))
                post_id = post.get("id", "?")
                parts.append(f"  {i+1}. [{author}] {title}")
                if content:
                    parts.append(f"     {content}")
                parts.append(f"     Likes: {likes} | ID: {post_id}")

        # Mentions
        mentions = obs.get("mentions", [])
        if mentions:
            parts.append(f"\nMENTIONS ({len(mentions)}):")
            for m in mentions[:3]:
                parts.append(f"  - {m.get('title', m.get('content', '?')[:100])}")

        # Constitutional topics
        relevant = obs.get("relevant", [])
        if relevant:
            parts.append(f"\nCONSTITUTIONAL DISCUSSIONS ({len(relevant)}):")
            for r in relevant[:3]:
                parts.append(f"  - {r.get('title', r.get('content', '?')[:100])}")

        if not parts:
            return "No observations available."

        return "\n".join(parts)

    # =========================================================================
    # Task 3: L2 Expiry Check (every 15 min)
    # =========================================================================

    async def _l2_expiry_loop(self):
        """Expire old L2 actions and process retries."""
        while self._running:
            try:
                await asyncio.sleep(L2_EXPIRY_CHECK_SECONDS)
                self.agent.action_queue.expire_old_actions()
                
                # Process retry queue (Feature C)
                retry_results = self.agent.action_queue.process_retries()
                if retry_results:
                    logger.info(f"Processed {len(retry_results)} retried action(s)")
                    for r in retry_results:
                        status = r.get("status", "?")
                        action_id = r.get("action_id", "?")
                        await self._notify(
                            f"🔄 Retry result: #{action_id} → {status}"
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"L2 expiry/retry check error: {e}")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _check_daily_reset(self):
        """Reset daily action counter at midnight UTC."""
        today = datetime.utcnow().date()
        if today != self._daily_reset_date:
            self._daily_action_count = 0
            self._daily_reset_date = today
            logger.info("Daily action counter reset")

    def get_status(self) -> Dict:
        """Get autonomy loop status."""
        return {
            "running": self._running,
            "tasks_count": len(self._tasks),
            "daily_actions": self._daily_action_count,
            "daily_limit": MAX_AUTONOMOUS_ACTIONS_PER_DAY,
            "last_reflection": self._last_reflection_result,
            "has_observations": self._last_observations is not None,
        }

    # =========================================================================
    # Manual triggers (callable from Telegram)
    # =========================================================================

    async def trigger_heartbeat(self) -> str:
        """Manually trigger a heartbeat cycle."""
        await self._do_heartbeat()
        return "Heartbeat completed"

    async def trigger_reflection(self) -> str:
        """Manually trigger a reflection cycle."""
        await self._do_reflection()
        return "Reflection completed"
