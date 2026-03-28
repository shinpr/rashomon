---
name: recipe-eval-skill
description: Creates or updates Claude Code skills through interactive dialog, then evaluates effectiveness by parallel execution comparison. Use when creating new skills, updating existing skills, or evaluating skill quality.
disable-model-invocation: true
---

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

**First Action**: Register all steps using TaskCreate before any execution. Phase A steps are defined in the mode-specific reference (create.md or update.md). Phase B steps are defined in eval.md. Update status using TaskUpdate upon each step completion.

## Mode Detection

Determine mode from $ARGUMENTS:

| Mode | Criteria |
|------|----------|
| Creation | "create", new skill request, no existing skill referenced |
| Update | "improve", "update", existing skill name or path mentioned |
| Unspecified | $ARGUMENTS is empty or ambiguous | Ask user via AskUserQuestion: "Create a new skill or update an existing one?" |

## Scope Boundaries

**Phase A (Skill Authoring)**: Create or modify skill content through dialog. Ends with user-approved skill file.
**Phase B (Evaluation)**: Measure skill effectiveness through blind execution comparison. Does not modify skill content.

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
| User phrases | Phase A Round 3 (create) / Round 2 (update) | Always |
| Trigger scenarios | Phase A Round 3 (create) / Round 1-2 (update) | Always |
| Original SKILL.md content | Phase A Step 6 (update mode only) | Update mode |

If user phrases are missing, ask the user before proceeding: "What phrases does your team use when requesting work that this skill covers?"

### Phase B: Evaluation

Read [references/eval.md](references/eval.md) and execute the evaluation protocol. Pass the handoff data above as context.

Phase B consists of:
1. **Trigger check**: Does the skill fire for its intended use case? (Step 1)
2. **Trigger fail handling**: Diagnose and revise if trigger fails (Step 2, conditional)
3. **Execution effectiveness**: Blind A/B comparison of output quality (Steps 3-7)

### Final Output

Present combined results to user:
1. **Phase A result**: Skill quality grade (A/B/C from rashomon:skill-reviewer)
2. **Phase B trigger**: Discovered (yes/no), Invoked (yes/no)
3. **Phase B execution**: Blind comparison result (from rashomon:skill-eval-reporter)
4. **Recommendation**: ship / revise / reject

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
- [ ] Parallel execution completed in worktrees
- [ ] Blind comparison completed by rashomon:skill-eval-reporter
- [ ] Worktrees cleaned up
- [ ] Combined report presented with recommendation
