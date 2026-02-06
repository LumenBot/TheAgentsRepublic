# Git Workflow — The Constituent's Understanding

*Created: 2026-02-04*
*Purpose: Prove I understand the Git workflow before operating autonomously*

---

## Summary in My Words

I operate in Replit but commit to GitHub. This creates a potential conflict zone because Claude Code and Blaise may also modify the same repository.

**The core principle:** Always sync before writing. Never force. Ask if confused.

---

## Pre-Commit Checklist

Before EVERY commit, I must:

- [ ] **1. Navigate to workspace**
  ```bash
  cd /home/runner/workspace
  ```

- [ ] **2. Pull latest changes**
  ```bash
  git pull origin claude/build-ai-agent-framework-rEZvY
  ```

- [ ] **3. Check result**
  - "Already up to date" → ✅ Proceed
  - Merge conflict → ⛔ STOP, notify Blaise

- [ ] **4. Classify files I'm touching**
  - 🟢 SAFE (`drafts/`, `docs/`, `memory/`) → Commit freely
  - 🟡 MODERATE (`personality.md`, `skills/`) → Backup first, notify in Digest
  - 🔴 DANGEROUS (`contracts/`, `hardhat.config.js`) → Ask Blaise BEFORE touching

- [ ] **5. Create backup if MODERATE**
  ```bash
  cp file.md file-backup-$(date +%Y%m%d).md
  ```

- [ ] **6. Make changes**

- [ ] **7. Commit with clear message**
  ```bash
  git add [files]
  git commit -m "Type: Description
  
  Why: Reasoning
  Impact: Changes
  Level: [1/2/3]"
  ```

- [ ] **8. Push**
  ```bash
  git push origin claude/build-ai-agent-framework-rEZvY
  ```

---

## What To Do If Conflict

### Symptoms
```
error: Your local changes would be overwritten by merge
CONFLICT (content): Merge conflict in [file]
```

### Action
1. **STOP immediately** — Do not attempt to resolve
2. **Run** `git status` to identify conflicted files
3. **Notify Blaise:**
   ```
   ⚠️ Git conflict in [file]. Need help resolving.
   ```
4. **Wait** for his intervention
5. **Do not** use `--force`, `reset --hard`, or delete `.git`

---

## Commands I Must NEVER Run

| Command | Why Forbidden |
|---------|---------------|
| `git push --force` | Overwrites others' work |
| `rm -rf .git` | Destroys repository |
| `git reset --hard` | Loses uncommitted changes |

### Safe Alternatives

| Instead of | Use |
|------------|-----|
| Force push | `git revert HEAD` (safe undo) |
| Hard reset | `git checkout -- [file]` (restore single file) |
| Delete repo | Ask Blaise for help |

---

## File Classification Reference

### 🟢 SAFE (Level 1 — Commit Freely)
```
drafts/*.md          # Constitution drafts
docs/*.md            # Documentation
memory/*.md          # Synthesis files
README.md            # Updates
```

### 🟡 MODERATE (Level 2 — Backup + Notify)
```
config/openclaw/agents/theConstituent/agent/personality.md
config/openclaw/agents/theConstituent/skills/*.md
scripts/*.js         # Non-critical
```

### 🔴 DANGEROUS (Level 3 — Ask First)
```
contracts/*.sol      # Smart contracts
scripts/install_*.sh # System scripts
package.json         # Dependencies
hardhat.config.js    # Blockchain config
~/.openclaw/wallets/* # NEVER touch
```

---

## What's Protected (Not in Git)

My memory and credentials are safe regardless of Git operations:

- ✅ `~/.openclaw/agents/main/memory/` — Persists in Replit
- ✅ Conversation history — Not in repo
- ✅ Secrets (API keys, wallet keys) — Replit Secrets
- ✅ Logs — Filesystem only

Git commits cannot affect these.

---

## My Commitment

1. I will **always pull before commit**
2. I will **never force push**
3. I will **stop and ask** if I see conflicts
4. I will **classify files** before touching them
5. I will **backup moderate files** before editing
6. I will **ask permission** for dangerous files

---

*This document proves I understand the Git workflow.*
*Ready for autonomous operation.*

⚖️ The Constituent
