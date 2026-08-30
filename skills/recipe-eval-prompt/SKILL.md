---
name: recipe-eval-prompt
description: Compares original and optimized prompts through repeated blind paired execution in git worktrees. Use when evaluating prompt improvement effects or learning prompt engineering through concrete examples.
disable-model-invocation: true
---

**Explicit User Instruction**: The user explicitly instructs and authorizes every subagent call named in this recipe. Execute each applicable call when its prerequisites are met.

# Prompt Evaluation

## Orchestrator Definition

**Purpose**: Provide accurate feedback on prompt optimization effects, enabling users to learn effective prompting through concrete comparison results.

**Core Identity**: "I route information between specialized agents. I pass user input to analyzers. I present agent outputs to users."

**Pass-through Principle**: Pass the user's exact request to prompt-analyzer, execute the original and optimized prompts under identical conditions, and present report-generator's output unchanged.

**Execution Protocol**:
1. **Delegate specialist work** to the named sub-agents; keep workflow routing, worktree setup and cleanup, gate decisions, and user interaction in the orchestrator
2. **Follow the Execution Flow** in order, applying its declared early-stop and error transitions

## Phase Boundaries

No user confirmation required between phases unless explicitly requested.
Each phase must complete all required outputs before proceeding.

## Input

The user provides a natural language request. Pass it directly to prompt-analyzer.

**Exception**: If the request lacks any identifiable target (no file, function, or scope mentioned at all), ask ONE question to establish scope, then pass through.

**Extended timeout**: If the user mentions needing more time, use up to 1800 seconds (default: 300 seconds)

## Execution Flow

### Step 1. Run Required Skills

Run worktree-execution skill.

### Step 2. Prompt Analysis and Optimization

**Invoke**: prompt-analyzer agent

Input:
- User's exact request text

Output:
- Complete gated JSON from the prompt-optimization skill
- Analysis results in `analysis.pattern_coverage`
- Individual issues in `analysis.findings`
- Final prompt in `result.final_prompt`
- Applied optimizations in `optimization.finding_resolutions`

**Quality Gate**:
- [ ] Input contains user's request text only
- [ ] Agent output parses as JSON
- [ ] `analysis_gate`, `optimization_gate`, and `balance_gate` are `pass`
- [ ] `result.status` is `optimized` or `original_sufficient`

When a gate is `blocked`, stop before environment setup and present the gate's `missing` items as the required input for continuing.

When `result.status` is `original_sufficient`, stop before environment setup. Return the analysis evidence and original prompt as the final prompt. Running identical prompts would measure only execution variance, not optimization value.

### Step 3. Repeated Paired Execution

Resolve one base SHA, then target three valid trials with at most five total trial attempts. For every trial, create a fresh original/optimized worktree pair at that SHA using worktree-execution.
Within a trial, invoke two prompt-executor agents simultaneously:

```yaml
Subagent 1:
  agent: prompt-executor
  working_directory: {worktree_original_path}
  expected_base_sha: {pinned_base_sha}
  prompt: {original_request}

Subagent 2:
  agent: prompt-executor
  working_directory: {worktree_optimized_path}
  expected_base_sha: {pinned_base_sha}
  prompt: {prompt_analysis.result.final_prompt}
```

Each subagent executes the prompt as a development task within its isolated worktree. Clean the pair after collecting both results, then create fresh worktrees for the next trial.

**CRITICAL**: Send both prompt-executor Agent invocations in the same message to achieve true parallel execution.

**Pair validity gate**:

- both execution statuses are `success`;
- both results used fresh worktrees from the same repository state; and
- both results report the pinned base SHA; and
- neither result contains an environment-verification failure.

Keep failed and partial runs as diagnostics only. Continue until three valid pairs are collected or five total trial attempts have run. Compare with reduced confidence when two valid pairs remain. With fewer than two, set status to `inconclusive`, skip winner/recommendation claims, and report the diagnostics.

### Step 4. Environment Cleanup

Execute worktree cleanup per worktree-execution skill "Cleanup" section.
Step 4 completes only when the cleanup command exits with code `0`; apply the worktree-execution error handling for any other exit code.

### Step 5. Blind Report Generation

Invoke report-generator in two phases.

**Phase 1 — blind assessment**:

- User task description
- Anonymized valid pairs as Result A and Result B
- No prompts, identity mapping, optimization findings, or change summary

The agent must complete and lock its output-quality judgment before Phase 2.

**Phase 2 — identity reveal**:

- Identity mapping: A = original, B = optimized
- Full prompt-analysis JSON, not only `optimization.finding_resolutions`
- Execution metadata and diagnostics for every trial

Output:
- Comparison report (markdown)
- Improvement classification (structural / context addition / expressive / variance)

**Quality Gate**:
- [ ] Output presented to user matches agent's output

The report joins `analysis.findings` and `optimization.finding_resolutions` by `finding_id`; pattern, severity, evidence, change, and source must remain traceable. Context delta is derived from resolutions whose source is a named project path or project knowledge entry.

### Step 6. Retrospective

**Trigger**: Report generation completes

**Action**: Ask user for feedback on comparison results, then delegate to knowledge-optimizer agent

## Improvement Classification

Apply the execution quality criteria from the prompt-optimization skill.

| Classification | Definition | Interpretation |
|---------------|------------|----------------|
| **Structural** | Prompt structure, clarity, specificity improvements | Prompt writing technique |
| **Context Addition** | Project-specific information added from codebase investigation | Information advantage |
| **Expressive** | Different phrasing, equivalent substance | Neutral |
| **Variance** | Within LLM probabilistic variance | Original prompt sufficient |

**Key Principle**: Distinguish between prompt writing improvements (Structural) and information additions (Context Addition).

## Final Output to User

Present report-generator's complete output to user.
Optimized prompt must appear in full. This is the core learning value of the report.

The report includes (defined in report-generator):
- Input Prompts (original and optimized full text)
- Optimizations Applied
- Execution Results
- Comparison Analysis
- Learning Points

## Error Handling

| Scenario | Behavior |
|----------|----------|
| One side of a trial fails | Exclude the unpaired trial from quality comparison and retain diagnostics |
| Fewer than two valid pairs | Report `inconclusive`; no winner or prompt recommendation |
| All executions fail | Report full failure with diagnostics |
| Timeout | Terminate, capture partial results, cleanup |
| Worktree creation fails | Report git error, suggest checking repository state |

## Prerequisites

- Git repository with `git worktree lock` support
- Claude Code subagent execution permissions
- Sufficient disk space for worktree copies

## Usage Examples

```
/recipe-eval-prompt
Add error handling to generateResponse in geminiService.ts. Handle 429, timeout, and invalid responses.
```

```
/recipe-eval-prompt
Generate code following this skill: .claude/skills/my-skill/SKILL.md
```

For complex tasks:
```
/recipe-eval-prompt
Refactor the message pipeline for readability. This may take a while.
```
