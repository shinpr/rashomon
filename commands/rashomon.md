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

## Phase Boundaries

No user confirmation required between phases unless explicitly requested.
Each phase must complete all required outputs before proceeding.

## Input

The user provides a natural language request. Pass it directly to prompt-analyzer.

**Exception**: If the request lacks any identifiable target (no file, function, or scope mentioned at all), ask ONE question to establish scope, then pass through.

**Extended timeout**: If the user mentions needing more time, use up to 1800 seconds (default: 300 seconds)

## Execution Flow

**TodoWrite Registration**: Register execution steps in TodoWrite and proceed systematically

### Step 1. Run Required Skills

Run worktree-execution skill.

### Step 2. Prompt Analysis and Optimization

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

### Step 3. Execution Environment Setup

Execute environment setup per worktree-execution skill "Creation" section.

### Step 4. Parallel Execution

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

### Step 5. Environment Cleanup

Execute worktree cleanup per worktree-execution skill "Cleanup" section.

### Step 6. Report Generation

**Invoke**: report-generator agent

Input:
- Original and optimized prompts
- Execution results from both subagents
- Applied optimizations list

Output:
- Comparison report (markdown)
- Improvement classification (structural / context addition / expressive / variance)

**Quality Gate**:
- [ ] Output presented to user matches agent's output

### Step 7. Retrospective

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
