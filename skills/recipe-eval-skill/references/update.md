# Update Mode Procedure

Steps for modifying an existing skill with targeted changes and optimization.

## Step 1: Identify Target Skill

1. Glob existing skills: `.claude/skills/*/SKILL.md`, `~/.claude/skills/*/SKILL.md`
2. If user specified a skill name or path: select it as target
3. If no match or ambiguous: list available skills and ask user to select
4. Read the target SKILL.md and inventory the complete skill directory, including references, scripts, assets, and other files
5. Present a brief summary of the skill's current scope and structure

## Step 2: Collect Modification Request

Collect the user's desired changes in 2-3 rounds.

**Round 1: Change Description**

If the user's initial prompt already describes the change and reason, acknowledge it and confirm understanding. Only ask what is missing:
- What changes do you want to make to this skill?
- Why is this change needed?

If a design decision with discrete options is needed (e.g., scope level, approach selection), use AskUserQuestion.

**Round 2: Held-Out Test Requests**

Present these questions as plain text and wait for the user's response:
- What complete requests does your team actually send for work this skill covers? Provide at least two skill-dependent requests verbatim. Keep them out of new description examples; Phase B uses one directly and reserves another for retesting after any authoring revision.

After collecting responses, classify each request as **skill-dependent** (requires the skill's knowledge) or **pattern-copyable** (can be completed by copying existing code). Ensure at least two complete skill-dependent requests. Hold both out from authoring examples.

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

Set both iteration inputs from the same review cycle:
- Initial modification: use the source skill from Step 1 as the content base and the Step 3 reviewer output as `Current review`.
- Grade C repair: use the preceding skill-creator output as the content base and the immediately preceding Step 5 reviewer output as `Current review`.

**Agent tool invocation**:
```
subagent_type: rashomon:skill-creator
description: "Apply skill modifications"
prompt: |
  Mode: modification
  Skill name: {target skill name}
  Existing content: {content base SKILL.md}
  Existing references:
  {for each file in content base references/: filename and content}
  {if no references exist: "No reference files"}
  Modification request: {user's change description from Step 2}
  User phrases for description: {non-held-out phrases from Round 2}
  Current review: {review selected for this iteration}
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

  Previous review:
  {prior skill-reviewer output, or "None"}

  Review resolutions:
  {skill-creator reviewResolutions, or "None"}
```

Present grade, findings, and principlesEvaluation to user.

**Decision logic**:
- Grade A/B → proceed to Step 6 and present remaining Grade B findings as optional notes
- Grade C → ask rashomon:skill-creator to resolve each finding by `findingId` as `apply`, `decline`, or `user_decision`
- `apply` → revise and re-review; `decline` → re-review with evidence; `user_decision` → ask the user
- A reviewer may maintain a declined finding only with new correctness or verifiability evidence; repeated preference is non-blocking
- Grade C after 2 repair/re-review iterations → present current content with remaining findings, let user decide

## Step 6: User Review and Write

1. Display the complete modified SKILL.md content in a fenced code block
2. Display a diff-style comparison between original and modified content
3. Display the `changesSummary` from rashomon:skill-creator output
4. Use AskUserQuestion: "Please review the changes above. Is there anything you'd like to adjust?"
5. If revision requested: collect specific feedback, return to Step 4
6. Immediately before the first write, create a byte-preserving snapshot of the complete source skill directory under a temporary root:
   - Compute the source-directory fingerprint before copying
   - Copy SKILL.md, references, scripts, assets, symlinks, and every other entry
   - Compute the snapshot fingerprint with eval-executor.py and require it to equal the source fingerprint; a mismatch blocks the write
   - Keep the snapshot read-only for Phase B
7. Upon approval, overwrite the target SKILL.md
   - If new references were created: write to `references/` directory
   - If existing references were modified: overwrite affected files
8. After all approved writes, compute and record the complete new source-directory fingerprint.

The old snapshot and new source directory are the only update-evaluation inputs. A saved SKILL.md string is insufficient because references, scripts, and assets affect execution.

Use a directory-preserving copy and compare both fingerprints before writing the source:

```bash
snapshot_root=$(mktemp -d "${TMPDIR:-/tmp}/rashomon-old-skill.XXXXXX")
python3 {plugin_path}/skills/recipe-eval-skill/scripts/eval-executor.py \
  --fingerprint-skill-dir "{source_skill_directory}"
cp -R "{source_skill_directory}" "$snapshot_root/{skill_name}"
python3 {plugin_path}/skills/recipe-eval-skill/scripts/eval-executor.py \
  --fingerprint-skill-dir "$snapshot_root/{skill_name}"
```

**Phase A complete. Proceed to eval.md for Phase B.**

## Phase B Handoff Data

Phase A must pass the following to Phase B (eval.md). The orchestrator carries these in context:

| Data | Source | Purpose |
|------|--------|---------|
| Skill name | Step 1 | `--skill-name` parameter |
| Source skill directory | Step 6 write location | Worktree copy source |
| Old skill directory snapshot | Step 6, captured before any write | Complete old-version input |
| Old directory fingerprint | Step 6 | Verify old installation identity |
| New directory fingerprint | Step 8 | Verify new installation identity |
| Held-out test requests | Round 2 (verbatim, skill-dependent) | Direct input for trigger and effectiveness checks |
| Other user phrases | Round 2 | Description authoring context; excluded from test selection |
| Trigger scenarios | Round 1-2 | Validate that the held-out request is in scope |

## Completion Criteria

- [ ] Target skill identified and read
- [ ] Modification request collected and confirmed
- [ ] Complete user requests collected and classified (at least two held-out skill-dependent requests)
- [ ] Current state analyzed by rashomon:skill-reviewer
- [ ] rashomon:skill-creator applied targeted modifications
- [ ] rashomon:skill-reviewer returned grade A or B for modified content
- [ ] User approved changes via diff review
- [ ] Modified file written to original location
- [ ] Complete original skill directory and fingerprint preserved for Phase B eval
