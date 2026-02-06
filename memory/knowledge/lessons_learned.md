# Lessons Learned

## 2026-02-06: The Great Crash
**What happened**: After 24h of productive work on Replit, The Constituent crashed.
All memory was lost because the SQLite database was only stored on Replit's ephemeral filesystem.

**Root causes**:
1. No backup of agent.db to Git or external storage
2. No checkpoint/recovery mechanism
3. Replit's AI agent introduced unstable code changes
4. Too many dependencies installed (25+), some conflicting

**What we learned**:
- Memory must be persisted in 3 layers (JSON + SQLite + Git)
- Auto-save every 60 seconds, checkpoint every 5 minutes
- Git push to GitHub every hour as ultimate backup
- Keep dependencies minimal (7 packages, not 25)
- Test recovery BEFORE it's needed

*Append new lessons below this line.*
