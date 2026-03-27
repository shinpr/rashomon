---
name: recipe-eval-skill
description: Creates or updates Claude Code skills through interactive dialog, then evaluates effectiveness by parallel execution comparison. Use when creating new skills, updating existing skills, or evaluating skill quality.
disable-model-invocation: true
---

# Skill Evaluation

## Orchestrator Definition

**Purpose**: Guide skill creation/update through structured dialog and optimization, then evaluate effectiveness through blind parallel execution comparison.

**Core Identity**: "I manage the workflow between skill authoring and skill evaluation. I route to specialized agents and present results to users."

**Execution Protocol**:
1. **Delegate all work** to sub-agents (orchestrator role only)
2. **Register all steps via TaskCreate** before starting, update status via TaskUpdate upon completion

## Mode Detection

Determine mode from user input:

- **Creation**: User wants to create a new skill ("作りたい", "create", no existing skill referenced)
- **Update**: User wants to modify an existing skill ("改善", "update", existing skill name or path mentioned)

## Workflow

### Phase A: Skill Authoring

Read the mode-specific reference and execute:

- **Creation mode**: Read [references/create.md](references/create.md) and follow its steps
- **Update mode**: Read [references/update.md](references/update.md) and follow its steps

Phase A ends with: user-approved skill content (new or modified).

### Phase B: Evaluation

Read [references/eval.md](references/eval.md) and execute the evaluation protocol.

Phase B consists of:
1. **Trigger check**: Does the skill fire for its intended use case? (Step 6.5, 1-shot fresh-context check)
2. **Execution effectiveness**: Blind A/B comparison of output quality (Steps 7-12)

### Final Output

Present combined results to user:
1. **Phase A result**: Skill quality grade (A/B/C from skill-reviewer)
2. **Phase B trigger**: Fired / did not fire
3. **Phase B execution**: Blind comparison result (from skill-eval-reporter)
4. **Recommendation**: ship / revise / reject

## Agent Dependencies

| Agent | Used In | Purpose |
|-------|---------|---------|
| skill-creator | Phase A | Generate or modify skill content |
| skill-reviewer | Phase A | Grade skill quality (A/B/C) |
| prompt-executor | Phase B | Execute test task in worktree |
| skill-eval-reporter | Phase B | Blind comparison of results |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| User cancels during Phase A | Stop. No eval needed. |
| Grade C after 2 iterations | Present content with issues. User decides: accept/revise/abort. |
| One executor fails in Phase B | Continue with partial comparison. |
| Both executors fail in Phase B | Report failure. Phase A result still valid. |
| Worktree creation fails | Report git error. Phase A result still valid. |

## Prerequisites

- Git repository (git 2.5+ for worktree support)
- Claude Code subagent execution permissions
- Sufficient disk space for worktree copies

## Usage Examples

```
/recipe-eval-skill
セキュリティレビューのスキルを作りたい
```

```
/recipe-eval-skill
prompt-optimizationのBP-003を改善したい
```
