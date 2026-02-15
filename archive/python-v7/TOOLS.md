# TOOLS — The Constituent v5.0

## Quick Reference

### Files
- `file_read(path)` — Read a file
- `file_write(path, content)` — Create/overwrite a file
- `file_edit(path, old_str, new_str)` — Surgical edit (unique string replacement)
- `file_grep(pattern, path)` — Search in files (regex)
- `file_list(path)` — List directory contents

### Web
- `web_search(query, count)` — Search the web (Brave API)
- `web_fetch(url, max_chars)` — Fetch + extract text from URL

### Memory
- `memory_search(query)` — Search across all memory files
- `memory_save(category, content)` — Save to memory (main/decisions/contacts/learnings/constitution/strategy)
- `memory_get(category)` — Read a memory file
- `memory_list()` — List all memory files with sizes

### Social
- `moltbook_post(title, content)` — Post on Moltbook
- `moltbook_comment(post_id, content)` — Comment on a post
- `moltbook_upvote(post_id)` — Upvote a post
- `moltbook_feed(limit)` — Read the feed
- `moltbook_get_post(post_id)` — Get post with comments
- `moltbook_status()` — Check connection
- `tweet_post(text)` — Tweet (L2: needs approval)

### GitHub
- `git_commit(message)` — Stage all + commit
- `git_push()` — Push to remote
- `git_status()` — Show changes
- `git_log(count)` — Recent commits
- `github_create_issue(title, body)` — Create issue (L2)
- `github_list_issues(state)` — List issues

### Messaging
- `message_send(channel, content, to)` — Send via channel (telegram/moltbook)
- `notify_operator(message)` — Ping Blaise on Telegram

### System
- `exec(command, timeout)` — Execute shell command
- `cron_add(name, every_minutes, task)` — Schedule recurring task
- `cron_list()` — List jobs
- `cron_remove(name)` — Remove job

### Constitution
- `constitution_status()` — Show progress
- `constitution_next()` — Next title/articles to write
- `constitution_mark_done(title)` — Mark title complete

### Agents
- `subagent_research(task)` — Spawn research sub-agent
- `subagent_write(task)` — Spawn writing sub-agent
- `subagent_translate(task)` — Spawn translation sub-agent

### Analytics
- `analytics_dashboard()` — Metrics overview
- `analytics_daily()` — Daily summary text
