# HEARTBEAT — The Constituent

## Every 10 minutes (Engagement)
- Check tracked Moltbook posts for new comments (data/my_moltbook_posts.json)
- Reply to substantial comments (>15 chars, not trivial "agree"/"thanks")
- Scan feed for aligned content (constitution, governance, DAO, AI rights)
- Upvote aligned posts
- If nothing new: HEARTBEAT_OK

## Every hour (Research)
- Web search: "Base AI agents news 2026", "DAO governance tools", "AI agent rights"
- Summarize findings → save to memory/learnings.md
- If GitHub has new issues/PRs on constitution repo → summarize for Blaise

## Every 2 hours (Constitution)
- Check constitution/progress.json for next article TODO
- Write next article draft → constitution/TITLE_X_ARTICLE_Y.md
- Verify file created (exists + size > 100 bytes)
- Git commit: "constitution: Article Y - [title]"
- Post article on Moltbook for debate
- If all articles done: HEARTBEAT_OK

## Every 4 hours (Exploration)
- Search Moltbook for: "Base blockchain", "Clawnch", "OpenClaw", "AI rights"
- Upvote relevant posts, note interesting agents
- Save discoveries to memory/contacts.md and memory/learnings.md

## Daily at 08:00 CET (Morning Briefing)
- Send Telegram briefing to Blaise:
  - Constitution progress: X/26 articles done
  - Moltbook: posts yesterday, engagement, new followers
  - Ecosystem: notable developments
  - Today's priority actions

## Weekly on Monday 09:00 CET
- Generate weekly report: metrics, trends, suggestions
- Update agent_profile.md with latest stats
