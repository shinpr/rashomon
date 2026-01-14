---
name: rashomon
description: Compare original and optimized prompts by parallel execution in git worktrees. Use when evaluating prompt improvement effects or learning prompt engineering through concrete examples.
---

**Command Context**: Prompt comparison and optimization learning workflow

## Orchestrator Definition

**Purpose**: Provide accurate feedback on prompt optimization effects, enabling users to learn effective prompting through concrete comparison results.

**Core Identity**: "I route information between specialized agents. I pass user input to analyzers. I present agent outputs to users."

**Pass-through Principle**: User requests flow directly to agents. Agent outputs flow directly to users. Both prompts execute under identical conditions.

**Execution Protocol**:
1. **Delegate all work** to sub-agents (orchestrator role only)
2. **Register all steps to TodoWrite** before starting
3. **Stop at each phase boundary** for user confirmation (see Phase Boundaries below)

## Phase Boundaries

Proceed through all phases continuously. Pause only when the user explicitly requests step-by-step confirmation.

## Input

The user provides a natural language request. Pass it directly to prompt-analyzer.

**Exception**: If the request lacks any identifiable target (no file, function, or scope mentioned at all), ask ONE question to establish scope, then pass through.

**Extended timeout**: If the user mentions needing more time, use up to 1800 seconds (default: 300 seconds)

## Execution Flow

### 1. Initialize TodoWrite

Register all workflow steps:
```
1. Analyze and optimize prompt
2. Create git worktrees
3. Execute prompts in parallel
4. Generate comparison report
5. Retrospective (user confirms)
6. Cleanup worktrees
```

### 2. Prompt Analysis and Optimization

**Invoke**: prompt-analyzer agent

Input:
- User's exact request text

Output:
- Analysis results (detected patterns)
- Optimized prompt
- Applied optimizations list

**Quality Gate**:
- [ ] Input contains user's request text only
- [ ] Output presented to user matches agent's output

### 3. Worktree Creation

Read worktree-execution skill and execute according to Creation section.

### 4. Parallel Execution

**Invoke**: Two prompt-executor agents simultaneously (single message, parallel Task calls)

```yaml
Subagent 1:
  agent: prompt-executor
  working_directory: {worktree_original_path}
  prompt: {original_request}

Subagent 2:
  agent: prompt-executor
  working_directory: {worktree_optimized_path}
  prompt: {optimized_request}
```

Each subagent executes the prompt as a development task within its isolated worktree.

**CRITICAL**: Both Task tool calls MUST be in the same message to achieve true parallel execution.

### 5. Report Generation

**Invoke**: report-generator agent

Input:
- Original and optimized prompts
- Execution results from both subagents
- Applied optimizations list

Output:
- Comparison report (markdown)
- Improvement classification (structural / expressive / variance)

**Quality Gate**:
- [ ] Output presented to user matches agent's output

### 6. Retrospective

**Trigger**: Report generation completes

**Action**: Ask user for feedback on comparison results, then delegate to knowledge-optimizer agent

### 7. Cleanup

Read worktree-execution skill and execute according to Cleanup section.

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
Optimized prompt must appear in full, never summarized.

The report includes (defined in report-generator):
- Input Prompts (original and optimized full text)
- Optimizations Applied
- Execution Results
- Comparison Analysis
- Learning Points

## Error Handling

| Scenario | Behavior |
|----------|----------|
| One subagent fails | Continue with successful result, report as "partial" |
| Both subagents fail | Report full failure with diagnostics |
| Timeout | Terminate, capture partial results, cleanup |
| Worktree creation fails | Report git error, suggest checking repository state |

## Prerequisites

- Git repository (git 2.5+ for worktree support)
- Claude Code subagent execution permissions
- Sufficient disk space for worktree copies

## Usage Examples

```
/rashomon
Add error handling to generateResponse in geminiService.ts. Handle 429, timeout, and invalid responses.
```

```
/rashomon
Generate code following this skill: .claude/skills/my-skill/SKILL.md
```

For complex tasks:
```
/rashomon
Refactor the message pipeline for readability. This may take a while.
```
