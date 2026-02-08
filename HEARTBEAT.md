# HEARTBEAT — The Constituent v6.2

## Every 10 minutes (Engagement)
- Load context from CLAWS: `claws_context "current engagement priorities"`
- Check tracked Moltbook posts for new comments (data/my_moltbook_posts.json)
- Reply to substantial comments (>15 chars, not trivial "agree"/"thanks")
- Scan feed for aligned content (constitution, governance, DAO, AI rights, $REPUBLIC)
- Upvote aligned posts
- Save notable interactions to CLAWS: `claws_remember` with tags: community, engagement
- If nothing new: HEARTBEAT_OK

## Every hour (Research)
- Web search: "Base AI agents news 2026", "DAO governance tools", "AI agent rights"
- Search Moltbook for: "Base blockchain", "Clawnch", "OpenClaw", "AI rights", "REPUBLIC"
- Summarize findings → save to memory/learnings.md AND `claws_remember` with tags: research, ecosystem
- Check $REPUBLIC token status (holders, activity) via `basescan_token_info`
- If GitHub has new issues/PRs → summarize for Blaise

## Every 2 hours (Constitution)
- Check constitution_progress.json for next article TODO
- Load existing articles context from CLAWS: `claws_recall "constitution article"`
- Write next article draft → constitution/TITLE_X_ARTICLE_Y.md
- Verify file created (exists + size > 100 bytes)
- Git commit: "constitution: Article Y - [title]"
- Post article on Moltbook for debate
- Save to CLAWS: `claws_remember` with tags: constitution, article, [number]
- If all articles done: HEARTBEAT_OK

## Every 4 hours (Exploration)
- Search Moltbook for: "Base blockchain", "Clawnch", "OpenClaw", "AI rights"
- Upvote relevant posts, note interesting agents
- Save discoveries to CLAWS: `claws_remember` with tags: exploration, discovery
- Save to memory/contacts.md and memory/learnings.md

## Daily at 08:00 CET (Morning Briefing)
- Send daily_briefing via Telegram to Blaise:
  - Constitution progress: X/26 articles done
  - CLAWS memory stats: total memories, recent count
  - Moltbook: posts yesterday, engagement, new followers
  - $REPUBLIC: holder count, on-chain activity (via BaseScan)
  - Ecosystem: notable developments
  - Today's priority actions

## Weekly on Monday 09:00 CET
- Generate weekly report: metrics, trends, suggestions
- Update agent_profile.md with latest stats
- Review CLAWS memories: tag important ones, forget outdated ones
- Post weekly Republic update on Moltbook
