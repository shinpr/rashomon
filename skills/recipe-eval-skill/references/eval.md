# Evaluation Protocol

Common evaluation procedure for both creation and update modes. Executes after Phase A (skill authoring) completes.

## Prerequisites from Phase A

- **Creation mode**: New skill file written to target location
- **Update mode**: Modified skill file written + original content preserved in memory

## Step 6.5: Trigger Check

Verify that the skill fires for its intended use case. This is a 1-shot existence check using a subagent with fresh context — not a simulation.

### Select Test Query

Pick one representative query from the trigger scenarios collected in Phase A (Round 2). Choose the most typical use case, not an edge case.

### Execute in Fresh Context

Create a worktree and ensure the skill is present, then spawn a single **prompt-executor** subagent:

```bash
./scripts/worktree-create.sh [repo_root] trigger-check trigger-check-unused
```

Use only the first worktree. Since the skill was just created in Phase A and may not be committed yet, copy the skill directory into the worktree if it doesn't exist:

```bash
# Copy skill to worktree if not present (uncommitted skills won't appear in worktree)
if [ ! -f "{worktree_trigger_path}/{skill_relative_path}" ]; then
  cp -r {source_skill_directory} {worktree_trigger_path}/{skill_directory}
fi
```

The subagent runs in an independent context with no prior conversation history:

```yaml
Task:
  agent: prompt-executor
  working_directory: {worktree_trigger_path}
  prompt: {selected_trigger_query}
```

### Evaluate

Check the `skills_referenced` field in the executor's structured output:

- **Fired**: Executor reports reading the target skill file → **pass**
- **Did not fire**: Executor does not report reading the target skill file → **fail**

If fail: the skill's description likely doesn't trigger for its intended use case. Suggest description rewrites applying Tier 1 guidelines from `prompt-optimization/references/skills.md`.

### Cleanup

```bash
./scripts/worktree-cleanup.sh [repo_root] {worktree_trigger_path}
```

Present trigger check result to user before proceeding to execution eval.

> **Future expansion**: Coverage-driven trigger eval with taxonomy-based query generation (multiple failure modes, coverage metrics). Requires trigger boundary taxonomy design as a prerequisite.

## Step 7: Determine Test Task

Select a test task automatically from the trigger scenarios collected in Phase A (Round 2). Choose a different scenario from the one used in Step 6.5 trigger check, to cover more ground. If only one scenario exists, reuse it.

If practical artifacts were provided in Phase A (e.g., specific files that need improvement), use those as the test task target — they represent the most realistic use case.

## Step 8: Create Worktrees

Use the worktree-execution skill to create two isolated environments.

Since the skill may not be committed yet, both modes require copying skill files into worktrees after creation.

**Creation mode**:
```bash
./scripts/worktree-create.sh [repo_root] baseline with-skill
```
- **worktree-A (baseline)**: Ensure no target skill exists (delete if present from a prior commit)
  ```bash
  rm -rf {worktree_a_path}/{skill_directory}
  ```
- **worktree-B (with-skill)**: Copy the new skill into the worktree if not already present
  ```bash
  cp -r {source_skill_directory} {worktree_b_path}/{skill_directory}
  ```

**Update mode**:
```bash
./scripts/worktree-create.sh [repo_root] old-version new-version
```
- **worktree-A (old-version)**: Write the original SKILL.md content (saved from Phase A) into the worktree
  ```bash
  cp -r {source_skill_directory} {worktree_a_path}/{skill_directory}
  # Then overwrite SKILL.md with the saved original content
  ```
- **worktree-B (new-version)**: Copy the updated skill into the worktree
  ```bash
  cp -r {source_skill_directory} {worktree_b_path}/{skill_directory}
  ```

## Step 9: Parallel Execution

Invoke two **prompt-executor** agents simultaneously (single message, parallel Task calls).

**CRITICAL**: Both Task tool calls MUST be in the same message for true parallel execution.

**Symmetric prompting**: Both tasks receive the same prompt. The only difference is the worktree contents (skill presence/absence or skill version).

```yaml
Task A:
  agent: prompt-executor
  working_directory: {worktree_a_path}
  prompt: {test_task_description}

Task B:
  agent: prompt-executor
  working_directory: {worktree_b_path}
  prompt: {test_task_description}
```

Skill usage is captured via prompt-executor's standard output format, which includes a required `skills_referenced` field. Both executors report this field — if no skills were read, they report "none".

## Step 10: Blind Comparison

Invoke **skill-eval-reporter** agent in two phases:

**Phase 1: Blind assessment** (Steps 1-3 in reporter)

```yaml
Input:
  resultA: {execution result from Task A}
  resultB: {execution result from Task B}
  evalMode: creation | update
  testTask: {test task description}
```

**CRITICAL**: Pass each executor's `execution_result` (status, outputs, artifacts, errors, observations) as "Result A" and "Result B". Exclude `skills_referenced` and `execution_context`. Do NOT reveal which is baseline/with-skill or old/new. The reporter evaluates purely on output quality and produces its Recommendation.

**Phase 2: Identity reveal + Skill usage analysis** (Step 4 in reporter)

After receiving the reporter's blind assessment, the orchestrator reveals the identity mapping and passes the skill usage self-reports:

```yaml
Follow-up:
  identityReveal: "Result A was {baseline|old-version}, Result B was {with-skill|new-version}"
  skillUsageA: {skills_referenced from Task A output}
  skillUsageB: {skills_referenced from Task B output}
  artifactsA: {artifacts from Task A output}
  artifactsB: {artifacts from Task B output}
```

The reporter then performs Skill Usage Analysis and Progressive Disclosure Assessment as Step 4.

## Step 11: Worktree Cleanup

Execute cleanup per worktree-execution skill:

```bash
./scripts/worktree-cleanup.sh [repo_root] {worktree_a_path} {worktree_b_path}
```

**Always execute cleanup**, even if evaluation fails.

## Step 12: Present Combined Report

Combine Phase A and Phase B results:

```markdown
# Skill Evaluation Summary

## Phase A: Skill Quality
- **Grade**: {A/B/C from skill-reviewer}
- **Key findings**: {summary of reviewer assessment}

## Phase B: Trigger Check (Step 6.5)
- **Query**: {the test query used}
- **Result**: {fired|did not fire}
{If did not fire: description rewrite suggestions}

## Phase B: Execution Effectiveness (Steps 7-12)
- **Winner**: {A/B/Neither} → revealed as {baseline|old → with-skill|new}
- **Assessment**: {clear winner / marginal / equivalent / trade-off}
- **Confidence**: {high/medium/low}

### Progressive Disclosure
{How efficiently was the skill's information loaded?}

### Skill Usage
{Which parts of the skill were actually referenced?}

## Recommendation
- **ship**: Grade A/B + skill shows clear improvement in Phase B
- **revise**: Grade B + marginal or no improvement in Phase B
- **reject**: Grade C, or skill shows no value above baseline
```
