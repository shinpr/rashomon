# Evaluation Protocol

Common evaluation procedure for both creation and update modes. Executes after Phase A (skill authoring) completes.

## Prerequisites from Phase A

- **Creation mode**: New skill file written to target location
- **Update mode**: Modified skill file written + original content preserved in memory

## Step 6.5: Trigger Precision Evaluation

Evaluate whether the skill's description correctly triggers (or avoids triggering) for relevant tasks. This tests the Tier 1 (metadata) quality of the skill.

### Build Test Cases

Ask the user to provide or confirm two sets of queries:

**should_trigger** (8-10 queries): Tasks where this skill SHOULD activate.
- Draw from the trigger scenarios collected in Phase A
- Include variations in phrasing and specificity

**should_not_trigger** (8-10 queries): Tasks where this skill should NOT activate.
- Adjacent domains that could be confused with this skill
- Generic tasks outside the skill's scope
- Tasks belonging to other existing skills

Example for a "security-review" skill:
```yaml
should_trigger:
  - "Review this code for SQL injection vulnerabilities"
  - "Check the authentication flow for security issues"
  - "Are there any XSS risks in this template?"
  # ...

should_not_trigger:
  - "Write unit tests for the login function"
  - "Refactor this function for readability"
  - "Add error handling to the API client"
  # ...
```

### Run Trigger Test

For each query, evaluate whether the skill's description would cause Claude to select this skill:

1. Present the skill's description alongside descriptions of other skills in the project (Glob existing skills)
2. For each test query, determine: would Claude select this skill based on description matching?
3. Record trigger/no-trigger for each query

### Score

| Metric | Calculation |
|--------|-------------|
| **Trigger rate** | (correct triggers) / (total should_trigger queries) |
| **False positive rate** | (incorrect triggers) / (total should_not_trigger queries) |
| **Precision** | (correct triggers) / (correct triggers + incorrect triggers) |

**Pass criteria**: Trigger rate ≥ 0.8 AND False positive rate ≤ 0.2

If the description fails: suggest description rewrites that improve trigger precision. Apply the Tier 1 guidelines from `prompt-optimization/references/skills.md`:
- Add specific trigger terms users actually type
- Add explicit "Use when:" scenarios
- Add negative space ("does NOT handle X") if false positives are high

Present trigger evaluation results to user before proceeding to execution eval.

## Step 7: Determine Test Task

Ask the user:

> "This skill's effectiveness will be measured by running a test task with and without the skill. Please specify a task that would demonstrate the skill's value."

If the user declines or says "skip", end here with Phase A results only.

## Step 8: Create Worktrees

Use the worktree-execution skill to create two isolated environments.

**Creation mode**:
```bash
./scripts/worktree-create.sh [repo_root] baseline with-skill
```
- **worktree-A (baseline)**: Delete the entire target skill directory from this worktree (SKILL.md + references/ + scripts/)
  ```bash
  rm -rf {worktree_a_path}/{skill_directory}
  ```
- **worktree-B (with-skill)**: Leave the skill file in place

**Update mode**:
```bash
./scripts/worktree-create.sh [repo_root] old-version new-version
```
- **worktree-A (old-version)**: Replace skill file with the original content (saved from Phase A)
  ```bash
  # Write the original SKILL.md content to worktree-A
  ```
- **worktree-B (new-version)**: Leave the updated skill file in place

## Step 9: Parallel Execution

Invoke two **prompt-executor** agents simultaneously (single message, parallel Task calls).

**CRITICAL**: Both Task tool calls MUST be in the same message for true parallel execution.

**Symmetric prompting**: Both tasks receive IDENTICAL prompts in both modes. No additional instructions, no reporting requests. The only difference is the worktree contents (skill presence/absence or skill version).

```yaml
Task A:
  agent: prompt-executor
  working_directory: {worktree_a_path}
  prompt: |
    {test_task_description}

Task B:
  agent: prompt-executor
  working_directory: {worktree_b_path}
  prompt: |
    {test_task_description}
```

## Step 9.5: Post-Execution Skill Usage Collection

After both tasks complete, collect skill usage data from each worktree **separately from the execution**. This avoids contaminating the execution prompt with reporting instructions.

For each worktree, check which skill files were accessed:

```bash
# List skill files that exist in the worktree
find {worktree_path}/skills -name "SKILL.md" 2>/dev/null
find {worktree_path}/.claude/skills -name "SKILL.md" 2>/dev/null

# Check git diff to see what files the executor read or modified
git -C {worktree_path} diff --name-only HEAD 2>/dev/null
```

Additionally, examine the executor's output for references to skill-specific terminology, section headings, or criteria IDs. This indirect evidence indicates which parts of the skill influenced behavior without having biased the execution.

Record for each worktree:
- **skills_present**: Skill files that existed in the worktree
- **artifacts_modified**: Files created or changed during execution
- **skill_influence_signals**: Skill-specific terminology or patterns observed in output

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

**CRITICAL**: Do NOT pass skill usage data in this phase. Pass results as "Result A" and "Result B" only. Do NOT reveal which is baseline/with-skill or old/new. The reporter evaluates purely on output quality and produces its Recommendation.

**Phase 2: Identity reveal + Skill usage analysis** (Step 4 in reporter)

After receiving the reporter's blind assessment, the orchestrator reveals the identity mapping and passes skill usage data:

```yaml
Follow-up:
  identityReveal: "Result A was {baseline|old-version}, Result B was {with-skill|new-version}"
  skillUsageA: {skill usage data collected in Step 9.5}
  skillUsageB: {skill usage data collected in Step 9.5}
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

## Phase B: Trigger Precision (Step 6.5)
- **Trigger rate**: {N/M} ({percentage})
- **False positive rate**: {N/M} ({percentage})
- **Precision**: {percentage}
- **Status**: {pass|fail}
{If fail: description rewrite suggestions}

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
