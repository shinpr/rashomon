<p align="center">
  <img src="assets/rashomon-banner.jpg" width="600" alt="Rashomon">
</p>

<p align="center">
  <a href="https://claude.ai/code"><img src="https://img.shields.io/badge/Claude%20Code-Plugin-purple" alt="Claude Code"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="License"></a>
</p>

**Know whether your skills actually improve agent behavior — not just look different.**

## Why rashomon?

> Inspired by the *Rashomon effect* — the idea that the same event can produce different outcomes depending on perspective.
> rashomon makes those differences explicit and comparable.

- Built a skill but unsure if it actually changes agent behavior?
- Iterating on skills and prompts by gut feel instead of evidence?
- Want repeatable evidence that your changes made things better, not just different?

**rashomon** evaluates skills and prompts through blind comparison — running tasks with and without your changes in isolated environments, then comparing real outputs without knowing which version produced which.

### Who Is This For?

rashomon is designed for:
- Skill authors who want evidence-based validation
- Developers using Claude Code daily
- Teams iterating on complex prompts (coding, analysis, writing)
- Anyone who wants **evidence**, not vibes, when improving skills and prompts

Not ideal if:
- You want one-shot prompt rewriting without comparison

## Quick Example

### Skill Evaluation

```
/recipe-eval-skill create
```

Creates a skill through interactive dialog, then evaluates effectiveness:

1. Collects domain knowledge, project-specific rules, and trigger phrases
2. Generates optimized skill content (graded A/B/C)
3. Runs up to three valid paired trials with and without the skill,
   using at most five attempts, then compares the outputs blindly

**What the evaluation report looks like:**

```
Skill Quality: Grade A
- Project-specific rules clearly encoded, no critical issues

Trigger Check: pass (loaded through the Skill tool or its SKILL.md file)

Execution Effectiveness:
- Winner: with-skill
- Assessment: repeatable structural improvement across valid pairs
- Key difference: Retry constraints and three-stage catch ordering were applied
  consistently (linked to skill Rules 3 and 6)

Recommendation: ship
```

```
/recipe-eval-skill api-error-handling skill's scope needs adjustment
```

Updates an existing skill, then evaluates old vs new version side by side.

See a real-world example: [I Built a Skill Reviewer. Then I Ran It on Itself.](https://dev.to/shinpr/i-built-a-skill-reviewer-then-i-ran-it-on-itself-4m4j)

### Prompt Evaluation

```
/recipe-eval-prompt Write a function to sort an array
```

Analyzes prompt issues, generates an improved version, and runs the original and optimized prompts
in up to three blind, paired trials. The report highlights differences that recur across trials.

<details>
<summary>Prompt Evaluation Details</summary>

#### What You Get

**1. Analysis**
```
- BP-002 (already satisfied): No consumer requirement selects a language,
  ordering, or error policy, so those choices remain flexible.
```

**2. Final Prompt**
```
Write a function to sort an array
```

**Result: Original sufficient** - Rashomon stops before paired execution because no outcome-relevant ambiguity was found.

</details>

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

### Skill Evaluation

```
/recipe-eval-skill create
```

Create a new skill and evaluate its effectiveness.

```
/recipe-eval-skill my-skill-name what to change
```

Update an existing skill and compare old vs new.

### Prompt Evaluation

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
Skill Evaluation (/recipe-eval-skill)
    ├── skill-creator (generates/modifies skills)
    ├── skill-reviewer (grades quality A/B/C)
    ├── eval-executor (up to 3 valid pairs, sequential within each pair)
    └── skill-eval-reporter (blind A/B comparison)

Prompt Evaluation (/recipe-eval-prompt)
    ├── prompt-analyzer (analyzes and optimizes)
    ├── prompt-executor (up to 3 valid pairs, parallel within each pair)
    └── report-generator (compares results)
```

<details>
<summary>Technical Details</summary>

### Isolated Execution

rashomon uses **git worktrees** to run both versions in completely separate environments. A worktree is a Git feature that creates independent working directories from the same repository—this ensures the two executions don't interfere with each other.

</details>

## Improvement Classification

Not all differences are improvements. rashomon classifies results into four categories:

| Classification | Meaning | Recommendation |
|---------------|---------|----------------|
| **Structural** | Real improvement in accuracy, completeness, or quality | Use the new version |
| **Context Addition** | One version had more project-specific knowledge | Useful if the context is accurate |
| **Expressive** | Different wording, same substance | Either version is fine |
| **Variance** | Just normal LLM randomness | Original was already good |

Classification is based on:
- Whether detected issues were resolved
- Output completeness and constraint adherence
- Agreement between blind quality assessment and observable output differences

<details>
<summary>Quality Patterns (BP-001 through BP-009)</summary>

Both skill review and prompt analysis check against 9 common patterns:

| Priority | Issues |
|----------|--------|
| **Critical** | Negative instructions, vague instructions, missing output format, unbounded work generation |
| **High Impact** | Unstructured prompts, missing or excess context, missing or excess procedural control |
| **Enhancement** | Unnecessary or biased examples, missing uncertainty handling |

### P1: Critical (Must Fix)

| ID | Pattern | Problem | Fix |
|----|---------|---------|-----|
| BP-001 | Negative Instructions | A prohibition can prime the forbidden behavior without naming the target state | Lead with the desired behavior; retain narrow prohibitions for irreversible actions |
| BP-002 | Vague Instructions | An outcome-relevant decision has materially different plausible interpretations | Apply the least-restrictive sufficient criterion that preserves valid solutions |
| BP-003 | Missing Output Format | No format spec leads to inconsistent outputs | Define expected structure: JSON schema, section headers, etc. |
| BP-009 | Unbounded Work Generation | Technically valid possibilities become unnecessary work | Keep only work required by the outcome, a boundary, a real consumer, or necessary proof |

### P2: High Impact (Should Fix)

| ID | Pattern | Problem | Fix |
|----|---------|---------|-----|
| BP-004 | Unstructured Prompt | Wall of text obscures priorities | Apply 4-block pattern: Context / Task / Constraints / Output Format |
| BP-005 | Missing or Excess Context | Missing facts force guesses; excess facts obscure operative instructions | Supply decision-sufficient context and condense the rest |
| BP-006 | Missing or Excess Procedural Control | Missing gates permit invalid transitions; excess gates prescribe reversible routes | Keep boundary gates and let evidence guide reversible routes |

### P3: Enhancement (Could Fix)

| ID | Pattern | Problem | Fix |
|----|---------|---------|-----|
| BP-007 | Unnecessary or Biased Examples | Generic examples consume context and anchor unrelated details | Use examples only for non-obvious domain or organization-specific mappings |
| BP-008 | Missing Uncertainty Handling | Unknown inputs have no defined next action | Classify evidence and stop at a gate when required input is unresolved |

Prompt optimization keeps analysis, optimization, and balance state in one invocation. Machine mode returns the gated JSON state; Interactive mode returns the user-facing result.
It avoids intermediate analysis files, so the skill does not depend on a specific agent or filesystem layout.

</details>

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
