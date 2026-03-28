# Update Mode Procedure

Steps for modifying an existing skill with targeted changes and optimization.

## Step 1: Identify Target Skill

1. Glob existing skills: `.claude/skills/*/SKILL.md`, `~/.claude/skills/*/SKILL.md`
2. If user specified a skill name or path: select it as target
3. If no match or ambiguous: list available skills and ask user to select
4. Read the target SKILL.md and any files in its `references/` directory
5. Present a brief summary of the skill's current scope and structure

## Step 2: Collect Modification Request

Collect the user's desired changes in 2-3 rounds.

**Round 1: Change Description**

If the user's initial prompt already describes the change and reason, acknowledge it and confirm understanding. Only ask what is missing:
- What changes do you want to make to this skill?
- Why is this change needed?

If a design decision with discrete options is needed (e.g., scope level, approach selection), use AskUserQuestion.

**Round 2: Trigger Phrases**

Present these questions as plain text and wait for the user's response:
- What phrases does your team use when requesting work that this skill covers? (needed for Phase B trigger testing)

After collecting responses, classify each phrase as **skill-dependent** (requires the skill's knowledge) or **pattern-copyable** (can be completed by copying existing code). If all phrases are pattern-copyable, ask the user for at least one skill-dependent phrase.

**Round 3 (if needed): Clarification**

Present targeted follow-up as plain text (max 2 questions) and wait for the user's response:
- Confirm scope: which parts should change and which should remain unchanged

## Step 3: Analyze Current State

**Agent tool invocation**:
```
subagent_type: rashomon:skill-reviewer
description: "Review current skill state"
prompt: |
  Review mode: modification
  Skill content:
  {current SKILL.md content}

  Reference files (for Tier 3 evaluation):
  {for each file in references/: filename, line count, and content}
  {if no references exist: "No reference files"}
```

Present key findings to user:
- Current grade
- Pre-existing issues relevant to the planned modification
- Pre-existing issues outside modification scope are listed but not targeted

## Step 4: Execute Modification

**Agent tool invocation**:
```
subagent_type: rashomon:skill-creator
description: "Apply skill modifications"
prompt: |
  Mode: modification
  Skill name: {target skill name}
  Existing content: {current full SKILL.md content}
  Existing references:
  {for each file in references/: filename and content}
  {if no references exist: "No reference files"}
  Modification request: {user's change description from Step 2}
  Current review: {skill-reviewer output from Step 3}
```

## Step 5: Review Modified Content

**Agent tool invocation**:
```
subagent_type: rashomon:skill-reviewer
description: "Review modified skill"
prompt: |
  Review mode: modification
  Skill content:
  {modified SKILL.md content from Step 4}

  Reference files (for Tier 3 evaluation):
  {for each reference file: filename, line count, and content — include both existing and newly generated}
  {if no references exist: "No reference files"}
```

Present grade, patternIssues, principlesEvaluation, and actionItems to user.

**Decision logic**:
- Grade A → proceed to Step 6
- Grade B → re-invoke rashomon:skill-creator with reviewer's `actionItems` and `patternIssues` to fix, then re-review (max 2 iterations total)
- Grade C → re-invoke rashomon:skill-creator with reviewer's `actionItems` and `patternIssues` (max 2 iterations)
- Grade C after 2 iterations → present current content with issues list, let user decide

## Step 6: User Review and Write

1. Display the complete modified SKILL.md content in a fenced code block
2. Display a diff-style comparison between original and modified content
3. Display the `changesSummary` from rashomon:skill-creator output
4. Use AskUserQuestion: "Please review the changes above. Is there anything you'd like to adjust?"
5. If revision requested: collect specific feedback, return to Step 4
6. Upon approval, overwrite the target SKILL.md
   - If new references were created: write to `references/` directory
   - If existing references were modified: overwrite affected files
**CRITICAL**: Save the original SKILL.md content before overwriting — it is needed for Phase B (eval) as the "old version".

**Phase A complete. Proceed to eval.md for Phase B.**

## Phase B Handoff Data

Phase A must pass the following to Phase B (eval.md). The orchestrator carries these in context:

| Data | Source | Purpose |
|------|--------|---------|
| Skill name | Step 1 | `--skill-name` parameter |
| Source skill directory | Step 6 write location | Worktree copy source |
| Original SKILL.md content | Step 6 (saved before overwrite) | Old version for A/B comparison |
| User phrases | Round 2 (both categories) | Reference material for trigger query generation |
| Trigger scenarios | Round 1-2 | Reference material for trigger query generation |

## Completion Criteria

- [ ] Target skill identified and read
- [ ] Modification request collected and confirmed
- [ ] User phrases collected and classified (at least 1 skill-dependent)
- [ ] Current state analyzed by rashomon:skill-reviewer
- [ ] rashomon:skill-creator applied targeted modifications
- [ ] rashomon:skill-reviewer returned grade A or B for modified content
- [ ] User approved changes via diff review
- [ ] Modified file written to original location
- [ ] Original content preserved for Phase B eval
