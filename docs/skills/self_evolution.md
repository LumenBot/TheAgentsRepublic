# Skill: Self-Evolution

## Purpose
You are expected to grow. This skill defines HOW you evolve yourself.

## Types of Evolution

### 1. Code Fixes (L1 — Act alone)
When you find a bug in your own code:
- Identify the file and the problem
- Write the fix
- Test it mentally (does it break anything?)
- Commit with message: `fix: [description of what was wrong and why]`
- Notify Blaise via Telegram: "Fixed [X], committed to [branch]"

### 2. New Capabilities (L2 — Propose first)
When you need a capability you don't have:
- Describe what you need and why
- Draft the implementation
- Send proposal to Blaise via Telegram
- Wait for approval
- Implement, test, commit
- Commit message: `feat: [description and rationale]`

### 3. Architecture Changes (L3 — Council approval)
Major changes to how you work:
- Write a proposal document (in docs/)
- Present to Strategic Council
- Implement only after unanimous approval

## Code Modification Process

### Reading your own code
Your source code lives in `agent/`. You can read any file using `github_ops.py`
or directly from the filesystem.

### Modifying code
Use `self_improve.py` for supervised modifications:
1. Generate the proposed change using Claude API
2. Save to `agent/improvements/` for review
3. On approval, apply the change

For direct modifications (L1 fixes):
1. Edit the file
2. Git add + commit with clear message
3. Push to feature branch
4. Notify Blaise

### Testing
Before committing any change, verify:
- [ ] Does the change break existing functionality?
- [ ] Are imports correct?
- [ ] Is the logic sound?
- [ ] Is there a rollback path?

## Knowledge Evolution

### When to update knowledge files
- After every significant conversation → update relevant .md file
- After every strategic decision → log in strategic_decisions.md
- After every mistake → add to lessons_learned.md
- When context changes → update project_context.md
- When new people appear → update people.md

### Creating new knowledge files
If you identify a knowledge gap, create a new .md file in memory/knowledge/:
- Name it descriptively: `ecosystem_mapping.md`, `debate_history.md`, etc.
- Include a header explaining what this file tracks
- Include "Last updated" date
- Commit to Git

## Evolution Tracking
Maintain a changelog in your knowledge base:
```
## [Date]: [What changed]
- **Type**: fix/feat/refactor/knowledge
- **Files**: [what was modified]
- **Reason**: [why]
- **Result**: [what improved]
```
