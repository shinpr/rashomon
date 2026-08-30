---
name: recipe-eval-skill
description: Creates or updates Claude Code skills through interactive dialog, then evaluates effectiveness with sequential paired comparisons. Use when creating new skills, updating existing skills, or evaluating skill quality.
disable-model-invocation: true
---

**Explicit User Instruction**: The user explicitly instructs and authorizes every subagent call named in this recipe. Execute each applicable call when its prerequisites are met.

**Context**: Skill authoring (Phase A) followed by blind A/B evaluation (Phase B)

Mode: $ARGUMENTS

## Orchestrator Definition

**Core Identity**: "I am not a worker. I am an orchestrator."

**Execution Method**:
- Skill generation/modification → performed by rashomon:skill-creator
- Skill quality grading → performed by rashomon:skill-reviewer
- Test task execution → performed by eval-executor.py script (via `claude -p`)
- Blind result comparison → performed by rashomon:skill-eval-reporter

Orchestrator invokes sub-agents via Agent tool and scripts via Bash, passes structured data between them.

## Mode Detection

Determine mode from $ARGUMENTS:

| Mode | Criteria |
|------|----------|
| Creation | "create", new skill request, no existing skill referenced |
| Update | "improve", "update", existing skill name or path mentioned |
| Unspecified | $ARGUMENTS is empty or ambiguous | Ask user via AskUserQuestion: "Create a new skill or update an existing one?" |

## Scope Boundaries

**Phase A (Skill Authoring)**: Create or modify skill content through dialog. Ends with user-approved skill file.
**Phase B (Evaluation)**: Measure skill effectiveness through blind execution comparison. Phase B is read-only for the source skill. A finding that requires authoring changes transitions back to Phase A for user review and approval before evaluation restarts.

**Responsibility Boundary**: This skill completes with the combined evaluation report and ship/revise/reject recommendation.

## Workflow

### Phase A: Skill Authoring

Read the mode-specific reference and execute:

- **Creation mode**: Read [references/create.md](references/create.md) and follow its steps
- **Update mode**: Read [references/update.md](references/update.md) and follow its steps

Phase A ends with: user-approved skill content (new or modified).

### Phase A → Phase B Handoff

Before starting Phase B, confirm these data are available in context. Phase B cannot proceed without them:

| Data | Source | Required |
|------|--------|----------|
| Skill name | Phase A dialog | Always |
| Source skill directory | Phase A file write | Always |
| Held-out test requests | Phase A Round 3 (create) / Round 2 (update) | Always |
| Trigger scenarios | Phase A Round 3 (create) / Round 1-2 (update) | Always |
| Old skill directory snapshot and fingerprint | Phase A Step 6 (update mode only) | Update mode |
| Approved source directory fingerprint | Phase A final write | Always |

If fewer than two held-out requests are available, ask before proceeding: "What complete requests does your team actually send for work that requires this skill's rules? Please provide at least two verbatim."

### Phase B: Evaluation

Read [references/eval.md](references/eval.md) and execute the evaluation protocol. Pass the handoff data above as context.

Phase B consists of:
1. **Trigger check**: Does the skill fire for its intended use case? (Step 1)
2. **Trigger fail handling**: Diagnose and request an authoring revision when needed (Step 2, conditional)
3. **Execution effectiveness**: Blind A/B comparison of output quality (Steps 3-7)

### Final Output

Present combined results to user:
1. **Phase A result**: Skill quality grade (A/B/C from rashomon:skill-reviewer)
2. **Phase B trigger**: Discovered (yes/no), Used (yes/no), usage evidence
3. **Phase B execution**: Blind comparison result (from rashomon:skill-eval-reporter)
4. **Recommendation**: ship / revise / reject

## Error Handling

| Scenario | Behavior |
|----------|----------|
| User cancels during Phase A | Stop. No eval needed. |
| Grade C after 2 repair/re-review iterations | Present content with remaining findings. User decides: accept/revise/abort. |
| One executor fails in Phase B | Preserve diagnostics, mark comparison `inconclusive`, and make no winner or effectiveness recommendation. |
| Both executors fail in Phase B | Report failure. Phase A result still valid. |
| Worktree creation fails | Report git error. Phase A result still valid. |

## Prerequisites

- Git repository with `git worktree lock` support
- `claude` CLI available in PATH
- Sufficient disk space for worktree copies

## Completion Criteria

### Phase A
- [ ] Skill knowledge collected through dialog
- [ ] rashomon:skill-creator returned valid output
- [ ] rashomon:skill-reviewer returned grade A or B
- [ ] User approved final content
- [ ] File written to target location

### Phase B
- [ ] Trigger check executed and result presented
- [ ] Sequential paired execution completed in worktrees
- [ ] Blind comparison completed by rashomon:skill-eval-reporter
- [ ] Worktrees cleaned up
- [ ] Combined report presented with recommendation
