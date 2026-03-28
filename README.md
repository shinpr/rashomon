<p align="center">
  <img src="assets/rashomon-banner.jpg" width="600" alt="Rashomon">
</p>

<p align="center">
  <a href="https://claude.ai/code"><img src="https://img.shields.io/badge/Claude%20Code-Plugin-purple" alt="Claude Code"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="License"></a>
</p>

**See what actually changes when you improve your prompts and skills — not just different wording.**

## Why rashomon?

> Inspired by the *Rashomon effect* — the idea that the same event can produce different outcomes depending on perspective.
> rashomon makes those differences explicit and comparable.

- Spending too much time on trial-and-error with prompts?
- Read best practices but not sure how they apply to your case?
- Want proof that your changes actually made things better?
- Building skills but unsure if they improve agent behavior?

**rashomon** analyzes, improves, and compares prompts and skills—so you can see what *actually* changed, and whether it matters. Unlike rule-based checks, rashomon evaluates real outputs through blind comparison (without knowing which version produced which output).

### Who Is This For?

rashomon is designed for:
- Developers using Claude Code daily
- Teams iterating on complex prompts (coding, analysis, writing)
- Skill authors who want evidence-based validation
- Anyone who wants **evidence**, not vibes, when improving prompts and skills

Not ideal if:
- You don't use git
- You want one-shot prompt rewriting without comparison

## Quick Example

### Prompt Evaluation

```
/recipe-eval-prompt Write a function to sort an array
```

### What You Get

**1. Detected Issues**
```
- BP-002 (Vague Instructions): Sort order, language, and error handling not specified
- BP-003 (Missing Output Format): No expected output structure defined
```

**2. Improved Prompt**
```
Write a TypeScript function that sorts a number array in ascending order.
- Return empty array for empty input
- Include JSDoc comments
- Output: function code with example usage
```

**3. Comparison Report**

| Aspect | Original | Improved |
|--------|----------|----------|
| Type definitions | None | Included |
| Edge case handling | None | Included |
| Documentation | None | JSDoc added |

**Result: Structural Improvement** - The optimization made a meaningful difference.

### Example: When rashomon finds no real improvement

```
/recipe-eval-prompt Summarize this article in 3 bullet points
```

**Result: Variance** - Prompt was already well-scoped; differences were stylistic only.

### Skill Evaluation

```
/recipe-eval-skill create
```

Creates a skill through interactive dialog, then evaluates effectiveness:
1. Collects domain knowledge, project-specific rules, and trigger phrases
2. Generates optimized skill content (graded A/B/C)
3. Runs a test task with and without the skill in isolated environments, using blind A/B comparison

**What the evaluation report looks like:**

```
Skill Quality: Grade A
- Project-specific rules clearly encoded, no critical issues

Trigger Check: pass (discovered + invoked)

Execution Effectiveness:
- Winner: with-skill
- Assessment: structural improvement
- Key difference: 3-stage catch ordering and retry constraints
  applied correctly (attributed to skill Rules 3 and 6)

Recommendation: ship
```

```
/recipe-eval-skill api-error-handling skill's scope needs adjustment
```

Updates an existing skill, then evaluates old vs new version side by side.

## Installation

> Requires [Claude Code](https://claude.ai/code) (this is a Claude Code plugin)

```bash
# 1. Start Claude Code
claude

# 2. Install the marketplace
/plugin marketplace add shinpr/rashomon

# 3. Install plugin
/plugin install rashomon@rashomon

# 4. Restart session (required)
# Exit and restart Claude Code
```

## Usage

```
/recipe-eval-prompt Your prompt here
```

From a file:
```
/recipe-eval-prompt Generate code following this skill: ./prompts/my-skill.md
```

For complex tasks that need more time, just mention it in natural language:
```
/recipe-eval-prompt Refactor the entire authentication module. This might take a while.
```

## How It Works

```
Your Prompt
    ↓
1. Analyze    → Detect common issues automatically
    ↓
2. Improve    → Generate optimized version
    ↓
3. Run Both   → Execute in isolated environments
    ↓
4. Compare    → Show what actually changed
    ↓
Comparison Report
```

<details>
<summary>Technical Details</summary>

### Isolated Execution

rashomon uses **git worktrees** to run both prompts in completely separate environments. A worktree is a Git feature that creates independent working directories from the same repository—this ensures the two executions don't interfere with each other.

### Architecture

```
Prompt Evaluation (/recipe-eval-prompt)
    ├── prompt-analyzer (analyzes and optimizes)
    ├── prompt-executor ×2 (isolated worktrees)
    └── report-generator (compares results)

Skill Evaluation (/recipe-eval-skill)
    ├── skill-creator (generates/modifies skills)
    ├── skill-reviewer (grades quality A/B/C)
    ├── eval-executor.py ×2 (isolated worktrees)
    └── skill-eval-reporter (blind A/B comparison)
```

</details>

## What It Detects

rashomon checks for 8 common prompt issues:

| Priority | Issues |
|----------|--------|
| **Critical** | Negative instructions ("don't do X"), vague instructions, missing output format |
| **High Impact** | Unstructured prompts, missing context, complex tasks without breakdown |
| **Enhancement** | Biased examples, no permission for uncertainty |

<details>
<summary>Pattern Details (BP-001 through BP-008)</summary>

### P1: Critical (Must Fix)

| ID | Pattern | Problem | Fix |
|----|---------|---------|-----|
| BP-001 | Negative Instructions | "Don't do X" often backfires—LLMs focus on what's mentioned | Reframe positively: "Don't include opinions" → "Include only factual information" |
| BP-002 | Vague Instructions | Missing specifics cause high output variance | Add explicit constraints: format, length, scope, tone |
| BP-003 | Missing Output Format | No format spec leads to inconsistent outputs | Define expected structure: JSON schema, section headers, etc. |

### P2: High Impact (Should Fix)

| ID | Pattern | Problem | Fix |
|----|---------|---------|-----|
| BP-004 | Unstructured Prompt | Wall of text obscures priorities | Apply 4-block pattern: Context / Task / Constraints / Output Format |
| BP-005 | Missing Context | No background leads to wrong assumptions | Add purpose, audience, relevant constraints |
| BP-006 | Complex Task | Undivided complex tasks have higher error rates | Break into steps with quality checkpoints |

### P3: Enhancement (Could Fix)

| ID | Pattern | Problem | Fix |
|----|---------|---------|-----|
| BP-007 | Biased Examples | Homogeneous examples cause overfitting | Diversify: include edge cases, different formats |
| BP-008 | No Uncertainty Permission | No "I don't know" option causes hallucination | Add: "If unsure, say so" |

</details>

## Improvement Classification

Not all differences are improvements. rashomon classifies results into four categories:

| Classification | Meaning | Recommendation |
|---------------|---------|----------------|
| **Structural** | Real improvement in accuracy, completeness, or quality | Use the optimized version |
| **Context Addition** | One version had more project-specific knowledge | Useful if the context is accurate |
| **Expressive** | Different wording, same substance | Either version is fine |
| **Variance** | Just normal LLM randomness | Original was already good |

Classification is based on:
- Whether detected issues (BP patterns) were resolved
- Output completeness and constraint adherence
- Agreement between blind quality assessment and observable output differences

<details>
<summary>About Knowledge Base</summary>

## Knowledge Base

rashomon learns from your project over time.

**Location**: `.claude/.rashomon/prompt-knowledge.yaml`

**How it works**:
- Automatically enabled when the file exists
- Stores project-specific patterns (not generic best practices)
- Referenced during analysis, updated after comparisons
- Max 20 entries, lowest-confidence ones removed first

**Key principle**: Old knowledge isn't automatically removed. Patterns that have worked for a long time are often the most valuable.

</details>

<details>
<summary>Troubleshooting</summary>

## Troubleshooting

### Leftover worktrees

If rashomon exits unexpectedly, temporary directories might remain:

```bash
# Worktrees are stored in system temp directory
# Clean up manually if needed:
rm -rf ${TMPDIR:-/tmp}/worktree-rashomon-*
```

### Timeout issues

For complex prompts that need more time, mention it when invoking:

```
/recipe-eval-prompt Complex task here. This might take longer than usual.
```

### "Not a git repository" error

rashomon requires a git repository. Initialize one with:

```bash
git init
```

</details>

## Requirements

- Git 2.5+
- Python 3.9+
- Claude Code
- Must run inside a git repository

## License

MIT
