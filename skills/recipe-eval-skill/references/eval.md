# Evaluation Protocol

Executes after Phase A (skill authoring) completes. Uses `scripts/eval-executor.py` to run prompts via `claude -p` with skill auto-discovery enabled.

## eval-executor.py Output Schema

```json
{
  "result": "final task output text",
  "status": "success | partial | error",
  "exit_code": 0,
  "skill_discovered": true,
  "skill_invoked": true,
  "files_modified": ["path/to/file"],
  "tools_used": ["Skill", "Read", "Write"],
  "error": "only on error or partial"
}
```

`files_modified` tracks Write, Edit, MultiEdit tool calls only. Bash-based file operations are not tracked.

## Prerequisites from Phase A

| Field | Source | How to resolve |
|-------|--------|----------------|
| Skill name | `name` field from skill frontmatter | Used as `--skill-name` parameter |
| Source skill directory | Where Phase A wrote the skill files | Absolute path to the directory containing SKILL.md |
| Original SKILL.md content | Update mode only: saved before overwrite in Phase A Step 6 | Stored in orchestrator context as string |
| Plugin path | Directory containing this plugin's `skills/` | Resolve via `Glob: **/recipe-eval-skill/scripts/eval-executor.py`, take parent 3 levels up |
| User phrases | Phrases collected in Phase A (skill-dependent and pattern-copyable) | Reference material for trigger query generation |
| Trigger scenarios | Scenarios collected in Phase A | Reference material for trigger query generation |

## First Action

Register Steps 1-7 using TaskCreate before any execution:

1. Orphan cleanup + Trigger check
2. Trigger fail handling (conditional)
3. Determine test task
4. Create worktrees + Parallel execution
5. Blind comparison
6. Worktree cleanup
7. Combined report

## Step 1: Orphan Cleanup + Trigger Check

### Orphan Cleanup

Clean up any leftover worktrees from previous runs:

```bash
./scripts/worktree-cleanup.sh --orphans [repo_root]
```

### Generate Trigger Query

Generate a test query that is likely to trigger skill invocation. The query must be one that the LLM would judge as requiring the skill's knowledge to complete.

**Inputs** (all are reference material, not direct sources):
- Skill description (from frontmatter)
- Skill content (key rules, patterns, terminology)
- User phrases from Phase A (how the team talks about this work)
- Trigger scenarios from Phase A

**Generation criteria**:
1. The query must use terminology that aligns with the skill's description — this is what the LLM matches against when deciding to invoke
2. The query must request work that cannot be completed by reading existing code alone (e.g., review against rules, implement a pattern not yet in the codebase)
3. Generate 3 candidate queries, select the one with highest coverage of the skill's core purpose

**Why generation instead of user phrases**: User phrases describe real usage scenarios but may not align with the description's terminology. The LLM decides to invoke based on description match, not on whether the skill's knowledge is theoretically needed.

### Execute

Create a worktree. The script creates two worktrees (required by its interface); use only the first:

```bash
./scripts/worktree-create.sh [repo_root] trigger-check trigger-check-unused
mkdir -p {worktree_trigger_path}/.claude/skills/
cp -r {source_skill_directory} {worktree_trigger_path}/.claude/skills/{skill_name}
```

Run:

```bash
python3 {plugin_path}/skills/recipe-eval-skill/scripts/eval-executor.py \
  --prompt "{selected_trigger_query}" \
  --cwd "{worktree_trigger_path}" \
  --skill-name "{skill_name}"
```

### Evaluate with Retry

Skill invocation is non-deterministic — the LLM may choose to read SKILL.md directly via Read tool instead of using the Skill tool. A single `skill_invoked: false` does not indicate a trigger problem. Retry up to 3 times with the same query before diagnosing.

**Per attempt**:
1. Create worktree, copy skill, run eval-executor.py (as above)
2. Clean up worktree:
```bash
./scripts/worktree-cleanup.sh [repo_root] {worktree_trigger_path}
```
3. Check result:
   - `skill_discovered: false` → Fix path and retry (does not count toward the 3 attempts)
   - `skill_invoked: true` → Trigger pass. Proceed to Step 3.
   - `skill_invoked: false` → Retry (create fresh worktree)

If `skill_invoked: false` after 3 attempts → Proceed to Step 2.

### Present Trigger Result

```
## Trigger Check Result
- **Query**: {selected_trigger_query}
- **Discovered**: {skill_discovered}
- **Invoked**: {skill_invoked}
- **Attempts**: {n}/3
- **Diagnosis**: {pass / proceeding to diagnosis}
```

## Step 2: Trigger Fail Handling (conditional)

Skip this step if trigger passed in Step 1.

This step is reached only after 3 consecutive `skill_invoked: false` results. At this point the cause is likely structural, not LLM non-determinism.

### Diagnose Root Cause

1. **Query-skill mismatch**: The query can be completed by reading existing code alone. → Generate a new query with stronger alignment to the skill's description. Re-run Step 1 (3-attempt cycle).

2. **General knowledge overlap**: The skill content restates knowledge the LLM already has. → Report to user: "This skill's content overlaps with the LLM's baseline knowledge. The skill needs project-specific rules or patterns to provide value." → Stop evaluation.

3. **Description mismatch**: The skill contains project-specific value but the description does not align with user intent. → Revise description (see below).

**Diagnostic flow**:
1. Check whether the query can be completed by reading existing code alone. If yes → #1.
2. Check whether the skill body contains project-specific content (class names, file paths, team conventions). If only general principles → #2. If specific content but description misaligned → #3.

### Description Revision (for cause #3, max 2 iterations)

1. Invoke rashomon:skill-creator to revise the description:
```
subagent_type: rashomon:skill-creator
description: "Revise skill description for trigger"
prompt: |
  Mode: modification
  Skill name: {skill_name}
  Existing content: {current full SKILL.md content}
  Modification request: The description failed to trigger auto-discovery
    after 3 attempts. Revise the description applying the Tier 1 description
    quality checklist from prompt-optimization/references/skills.md.
    User phrases for reference: {user_phrases from Phase A}.
    The revised description must focus on user intent and align with
    how users request this kind of work, while maintaining balance
    to avoid over-fitting to specific queries.
  Current review: {trigger fail diagnosis}
```

2. Invoke rashomon:skill-reviewer to verify the revised description.

3. Write the revised SKILL.md to the source skill directory.

4. Re-run Step 1 (3-attempt cycle) with the revised description.

**CRITICAL**: If trigger fails after 2 description revisions (each with 3-attempt cycles), stop evaluation. Report the trigger failure and recommend skill content revision.

## Step 3: Determine Test Task

Use the same query that passed trigger check in Step 1. Skill invocation is non-deterministic, so the A/B execution includes its own retry logic (Step 4). The trigger-checked query is the best available candidate.

## Step 4: Create Worktrees + Sequential Execution

### Create Worktrees

Skills must be at `.claude/skills/{skill_name}/` for auto-discovery.

**CRITICAL**: `{source_skill_directory}` is the directory Phase A wrote to. In update mode, this directory already contains the NEW version (Phase A overwrote it). The OLD version exists only as a string saved in orchestrator context.

**Creation mode**:
```bash
./scripts/worktree-create.sh [repo_root] baseline with-skill
# worktree-A (baseline): remove target skill from all discovery paths
rm -rf {worktree_a_path}/.claude/skills/{skill_name}
rm -rf {worktree_a_path}/skills/{skill_name}
# worktree-B (with-skill): copy new skill
mkdir -p {worktree_b_path}/.claude/skills/
cp -r {source_skill_directory} {worktree_b_path}/.claude/skills/{skill_name}
```

**Update mode**:
```bash
./scripts/worktree-create.sh [repo_root] old-version new-version
# worktree-A (old-version): copy current skill, then restore original SKILL.md
mkdir -p {worktree_a_path}/.claude/skills/
cp -r {source_skill_directory} {worktree_a_path}/.claude/skills/{skill_name}
```
Then use Write tool to overwrite `{worktree_a_path}/.claude/skills/{skill_name}/SKILL.md` with the original content string saved from Phase A.
```bash
# worktree-B (new-version): source_skill_directory already contains the updated version
mkdir -p {worktree_b_path}/.claude/skills/
cp -r {source_skill_directory} {worktree_b_path}/.claude/skills/{skill_name}
```

### Sequential Execution with Retry

**CRITICAL**: Execute sequentially. Do NOT parallelize with `&` or concurrent Task calls. Parallel `claude -p` invocations interfere with skill auto-discovery.

Each side must achieve `skill_invoked: true`. If `skill_invoked: false`, retry that side (up to 3 attempts) with a fresh worktree. The A/B comparison is only meaningful when both sides invoked the skill.

```bash
eval_tmpdir=$(mktemp -d)
```

**Side A** (retry until `skill_invoked: true`, max 3 attempts):
```bash
python3 {plugin_path}/skills/recipe-eval-skill/scripts/eval-executor.py \
  --prompt "{test_task_description}" \
  --cwd "{worktree_a_path}" \
  --skill-name "{skill_name}" > "$eval_tmpdir/result-a.json"
```
Check `skill_invoked` in result. If `false`, recreate worktree-A with same skill setup and re-run. After 3 failures, proceed with the best available result.

**Side B** (same retry logic):
```bash
python3 {plugin_path}/skills/recipe-eval-skill/scripts/eval-executor.py \
  --prompt "{test_task_description}" \
  --cwd "{worktree_b_path}" \
  --skill-name "{skill_name}" > "$eval_tmpdir/result-b.json"
```

After both complete, read the result files:
```bash
cat "$eval_tmpdir/result-a.json"
cat "$eval_tmpdir/result-b.json"
```

Parse each JSON and extract the `result` field for Step 5 Phase 1 and all fields for Step 5 Phase 2.

## Step 5: Blind Comparison

Invoke rashomon:skill-eval-reporter in two phases.

**Phase 1: Blind assessment**

**Agent tool invocation**:
```
subagent_type: rashomon:skill-eval-reporter
description: "Blind A/B comparison"
prompt: |
  Evaluate these two execution results purely on output quality.

  Test task: {test_task_description}
  Eval mode: {creation|update}

  Result A:
  {result field from result-a.json}

  Result B:
  {result field from result-b.json}
```

**CRITICAL**: Pass only `result` text in Phase 1. Metadata is reserved for Phase 2 after blind assessment completes.

**Phase 2: Identity reveal**

After reporter produces blind Recommendation, send follow-up via SendMessage:

```
Identity reveal:
  Result A = {baseline|old-version}
  Result B = {with-skill|new-version}

Metadata A:
  skill_discovered: {bool}
  skill_invoked: {bool}
  files_modified: {list}
  tools_used: {list}

Metadata B:
  skill_discovered: {bool}
  skill_invoked: {bool}
  files_modified: {list}
  tools_used: {list}

Perform Step 4 (Skill Usage Analysis) with this data.
```

## Step 6: Worktree Cleanup

```bash
./scripts/worktree-cleanup.sh [repo_root] {worktree_a_path} {worktree_b_path}
rm -rf "$eval_tmpdir"
```

Always execute, even on failure.

## Step 7: Combined Report

```markdown
# Skill Evaluation Summary

## Phase A: Skill Quality
- **Grade**: {A/B/C}
- **Key findings**: {summary}

## Phase B: Trigger Check
- **Query**: {query}
- **Discovered**: {yes/no}
- **Invoked**: {yes/no}
- **Diagnosis**: {pass / general knowledge overlap / description mismatch}

## Phase B: Execution Effectiveness
{Only present if trigger passed}
- **Winner**: {A/B/Neither} → {baseline|old → with-skill|new}
- **Assessment**: {clear winner / marginal / equivalent / trade-off}
- **Confidence**: {high/medium/low}

### Skill Usage
- **Baseline**: skill_invoked={bool}, tools_used={list}
- **With-skill**: skill_invoked={bool}, tools_used={list}

## Recommendation
- **ship**: Grade A/B + trigger pass + clear improvement
- **revise**: Grade B + trigger pass + marginal or no improvement
- **revise (trigger)**: Trigger fail due to description mismatch — revise description
- **revise (content)**: Trigger fail due to general knowledge overlap — add project-specific content
- **reject**: Grade C, or trigger fail persists after revision
```
