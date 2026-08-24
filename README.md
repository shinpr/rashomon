<p align="center">
  <img src="assets/rashomon-banner.jpg" width="600" alt="Rashomon">
</p>

<p align="center">
  <a href="https://claude.ai/code"><img src="https://img.shields.io/badge/Claude%20Code-Plugin-purple" alt="Claude Code"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="License"></a>
</p>

<p align="center">English | <a href="README.zh-CN.md">简体中文</a></p>

**Find out whether a skill improves agent behavior before you ship it.**

A capable model can follow a bad instruction very well. Unnecessary gates become unnecessary stops. Rigid procedures become extra work. Rules written around an older model's limitations can hold back a newer one.

In some cases, an agent performs better without the skill.

Rashomon tests that possibility. It runs the same task under a baseline and a changed version, then compares the results without revealing which version produced them. For skills, the result is a `ship`, `revise`, or `reject` recommendation.

Ready to try it? [Skip to installation.](#installation)

## Why this matters now

Skills and prompts change how an agent behaves at runtime. An instruction written to compensate for an older model can become redundant or actively harmful as models improve.

In one workflow, a generated task included the hard constraint `Do not improvise a workaround`. The executor stopped and escalated even though the smallest valid change fit inside the task. The orchestrator then had to add corrective guidance to the remaining 13 task prompts.

An LLM generated that constraint while following Rashomon's own prompt-optimization guidance. With the failed execution available as evidence, a later review followed the same guidance and identified the constraint as the cause. The paired evaluation was not used.

The fix was not another blanket rule. Generated constraints now require an authoritative source and must leave room for the smallest valid option. See [the resulting change](https://github.com/shinpr/claude-code-workflows/commit/4043a08) and [the wider design problem](https://www.norsica.jp/blog/when-better-models-make-old-agent-workflows-worse).

Review can catch problems visible in an instruction and diagnose failures after they happen. Rashomon pairs that review with execution evidence to answer the remaining question: does the instruction actually improve behavior before it ships?

## What Rashomon evaluates

| Evaluation | Comparison | Result |
|------------|------------|--------|
| New skill | Without the skill vs. with the skill | Whether the skill should ship |
| Updated skill | Previous version vs. revised version | Whether the revision is an improvement |
| Prompt | Original vs. optimized prompt | Whether optimization changes execution quality |

Rashomon can also conclude that the original prompt is already sufficient. A rewrite is not treated as an improvement by default.

## How the evidence is produced

The comparison focuses on observable results: correctness, completeness, constraint handling, and behavioral differences that recur across trials.

1. **Analyze the change.** Rashomon checks the skill or prompt for concrete instruction problems.
2. **Isolate execution.** Each version runs in a separate Git worktree from the same repository state.
3. **Run paired trials.** Repeated comparisons keep a single lucky result from deciding the outcome.
4. **Compare blind.** The evaluator judges output quality before learning which result came from which version.
5. **Make a recommendation.** Skill reports recommend `ship`, `revise`, or `reject`. Prompt reports return `Use optimized`, `Original sufficient`, `Needs refinement`, or `Collect more evidence`.

### Cost and limits

Prompt evaluation stops before paired execution if the original prompt is already sufficient. Otherwise, comparison runs real development tasks:

- Three valid pairs require six task executions.
- Invalid pairs can trigger retries, up to five total pair attempts and ten task executions.

Skill evaluation uses the same pair limits and also performs quality and trigger checks. These counts cover task executions in the paired comparison; total token use and duration depend on the task and the additional analysis.

Repeated blind trials help distinguish recurring behavior from one-off variance. They do not claim statistical significance or prove causality. Fewer than two valid pairs produce an inconclusive result.

### Example report format

```text
Skill Quality: Grade A
- Project-specific rules are encoded clearly with no critical issues

Trigger Check: pass

Execution Effectiveness:
- Winner: with-skill
- Assessment: repeatable structural improvement across valid pairs
- Key difference: retry constraints and three-stage catch ordering were applied
  consistently across trials

Recommendation: ship
```

Grade A means ready for use. Grade B is acceptable with noted improvements. Grade C requires revision before use.

## Installation

Rashomon is a [Claude Code](https://claude.ai/code) plugin.

```bash
# Start Claude Code
claude

# Add the marketplace
/plugin marketplace add shinpr/rashomon

# Install Rashomon
/plugin install rashomon@rashomon
```

Restart Claude Code after installation.

## Usage

### Create and evaluate a skill

```text
/recipe-eval-skill create
```

Rashomon collects the skill's purpose, domain knowledge, project-specific rules, and trigger phrases. It then creates the skill, reviews its quality, and compares agent behavior with and without it.

### Update and evaluate a skill

```text
/recipe-eval-skill <skill-name> <what to change>
```

For example:

```text
/recipe-eval-skill api-error-handling skill's scope needs adjustment
```

The current and revised versions are evaluated side by side.

### Evaluate a prompt

```text
/recipe-eval-prompt Add retry handling for HTTP 429 and 503 responses while preserving the client's public API
```

Rashomon analyzes the prompt, creates an optimized version when needed, and compares the original and optimized executions.

You can also evaluate a prompt stored in a file:

```text
/recipe-eval-prompt Generate code following this skill: ./prompts/my-skill.md
```

Rashomon is intended for cases where execution evidence matters. If you only need a one-off rewrite without comparison, the evaluation workflow is probably unnecessary.

## How results are classified

Different output does not necessarily mean better output. Rashomon separates four kinds of change:

| Classification | Meaning | Typical decision |
|----------------|---------|------------------|
| **Structural** | Accuracy, completeness, or execution quality improved | Use the new version |
| **Context Addition** | One version had useful project-specific knowledge | Use it when the context is accurate |
| **Expressive** | Wording changed but the result did not materially improve | Either version is acceptable |
| **Variance** | The difference is consistent with normal model variation | Keep the original or collect more evidence |

The report considers whether identified issues were resolved, whether required outputs and constraints were handled, and whether the same difference appeared across valid pairs.

<details>
<summary>Evaluation workflow details</summary>

### Skill evaluation

```text
/recipe-eval-skill
    ├── skill-creator: creates or updates the skill
    ├── skill-reviewer: grades content quality A, B, or C
    ├── eval-executor: runs paired trials
    └── skill-eval-reporter: performs the blind comparison
```

Skill trials run sequentially within each pair.

### Prompt evaluation

```text
/recipe-eval-prompt
    ├── prompt-analyzer: analyzes and optimizes the prompt
    ├── prompt-executor: runs paired executions in isolated worktrees
    └── report-generator: compares results and attributes differences
```

Prompt trials run in parallel within each pair.

### Isolated execution

Each version runs in its own Git worktree. Changes from one trial cannot affect the other trial's files, and both versions start from the same repository state.

</details>

<details>
<summary>Prompt and skill quality checks</summary>

Rashomon checks nine patterns that commonly reduce instruction quality.

| Priority | ID | Pattern | What Rashomon looks for |
|----------|----|---------|-------------------------|
| Critical | BP-001 | Negative instructions | A prohibition names the failure without defining the desired behavior |
| Critical | BP-002 | Vague instructions | An outcome-relevant choice has multiple plausible interpretations |
| Critical | BP-003 | Missing output format | A consumer needs a stable structure that the prompt does not define |
| Critical | BP-009 | Unbounded work generation | Instructions create work that the outcome does not require |
| High impact | BP-004 | Unstructured prompt | Important instructions are difficult to distinguish from supporting context |
| High impact | BP-005 | Missing or excess context | The model must guess, or relevant facts are buried in unrelated detail |
| High impact | BP-006 | Missing or excess procedural control | Required boundaries are absent, or reversible choices are over-prescribed |
| Enhancement | BP-007 | Unnecessary or biased examples | Examples consume context or anchor the model to an accidental detail |
| Enhancement | BP-008 | Missing uncertainty handling | Unknown inputs have no defined next action |

</details>

<details>
<summary>Project knowledge base</summary>

Rashomon can retain project-specific findings in:

```text
.claude/.rashomon/prompt-knowledge.yaml
```

The knowledge base:

- is enabled automatically when the file exists;
- stores project-specific patterns rather than generic advice;
- informs later analysis and can be updated from comparison results;
- keeps up to 20 entries and removes the lowest-confidence entries first.

Older knowledge is not removed solely because of age. A stable pattern with repeated support can remain useful.

</details>

<details>
<summary>Troubleshooting</summary>

### Leftover worktrees

If Rashomon exits unexpectedly, temporary worktrees may remain:

```bash
rm -rf ${TMPDIR:-/tmp}/worktree-rashomon-*
```

### Timeout issues

Prompt executions use a five-minute timeout by default. Mention that the task needs more time to allow up to 30 minutes:

```text
/recipe-eval-prompt Complex task here. This might take longer than usual.
```

The skill evaluation runner uses a ten-minute timeout per side. These limits are execution ceilings, not estimates of total evaluation time.

### "Not a git repository" error

Rashomon must run inside a Git repository. Initialize one with:

```bash
git init
```

</details>

## Requirements

- Claude Code
- Git 2.5 or later
- Python 3.9 or later, used by the skill evaluation runner
- A Git repository

## License

[MIT](LICENSE)
