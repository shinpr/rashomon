# Creation Mode Procedure

Steps for creating a new skill through interactive dialog and optimization.

## Step 1: Pre-flight Check

1. Glob existing skills: `.claude/skills/*/SKILL.md`, `~/.claude/skills/*/SKILL.md`
2. If user's topic matches an existing skill name: inform user and confirm whether to proceed or modify existing
3. List existing skill names for user awareness

## Step 2: Collect Skill Knowledge

Collect information through dialog in 5 rounds.

**Dialog method per round**:

| Round | Phase | Method |
|-------|-------|--------|
| 1-4 | Divergent | Present questions as plain text. Wait for user's free-form response. |
| 5 | Convergent | Present structured proposal. Use AskUserQuestion for confirmation. |

### Round 1: Skill Essence

Present these questions as plain text and wait for the user's response:
- What domain knowledge does this skill encode?
- What is the primary goal when this skill is applied?

### Round 2: Project-Specific Value

Assess whether the proposed skill adds value beyond the LLM's baseline knowledge.

Present these questions as plain text and wait for the user's response:
- What project-specific rules, patterns, class names, or workflows does this skill encode that the LLM would not know from general training?
- Provide concrete examples of what project-specific value looks like (e.g., specific error classes, team conventions, file patterns in this codebase)

| User response | Action |
|---------------|--------|
| Provides project-specific details | Incorporate into skill content. Proceed to Round 3. |
| Describes only general knowledge | Inform user that a general-knowledge-only skill is unlikely to trigger at runtime. Offer: (A) identify project-specific aspects to add, (B) proceed with the understanding that the skill may require iteration to trigger. |

### Round 3: Scope, Triggers, and User Phrases

Present these questions as plain text and wait for the user's response:
- When should this skill be activated? List 3-5 concrete scenarios
- What does this skill explicitly cover vs. what it leaves out?
- What phrases does your team actually use when requesting this kind of work? (e.g., "add error handling to X", "review the catch blocks", "fix the retry logic")

After collecting responses, classify each phrase into two categories:

| Category | Definition | Example |
|----------|-----------|---------|
| **Skill-dependent** | Cannot be completed correctly without the skill's knowledge; pattern-copying existing code would produce an incorrect or incomplete result | "implement retry logic", "review error handling" |
| **Pattern-copyable** | Can be completed by reading and copying existing code patterns | "add a fetchXxx function" |

If all phrases are pattern-copyable, inform the user: "These tasks can be completed by copying existing code. Can you provide a scenario that requires the hidden rules this skill encodes?" Ensure at least 1 skill-dependent phrase exists before proceeding.

**Phase B handoff**: Store both categories. Phase B uses these as reference material (not direct input) when generating trigger test queries.

### Round 4: Decision Criteria and Evidence

Present these questions as plain text and wait for the user's response:
- What are the concrete rules or criteria?
- Any examples of good/bad patterns?
- Any external references or standards?
- Practical artifacts: existing files, past failures, PRs, conversation logs that demonstrate the patterns. "Do you have any existing files, past failures, or documentation that demonstrate these patterns?"

### Round 5: Confirm Name and Structure

1. Derive skill name in gerund/noun form (e.g., `coding-standards`, `typescript-rules`)
2. Estimate size based on collected content volume
3. Present name and structure to user. Use AskUserQuestion for confirmation.

## Step 3: Generate Skill Content

**Agent tool invocation**:
```
subagent_type: rashomon:skill-creator
description: "Generate skill content"
prompt: |
  Mode: creation
  Skill name: {name from Round 5}
  Raw knowledge: {content from Round 4}
  Trigger scenarios: {scenarios from Round 3}
  User phrases: {team phrases from Round 3}
  Scope: {coverage and boundaries from Round 3}
  Decision criteria: {rules from Round 4}
  Practical artifacts: {files, failures, PRs from Round 4, if provided}
  Project-specific value: {details from Round 2}
```

## Step 4: Review and Fix

**Agent tool invocation**:
```
subagent_type: rashomon:skill-reviewer
description: "Review created skill"
prompt: |
  Review mode: creation
  Skill content:
  {skill-creator output assembled as full SKILL.md}

  Reference files (for Tier 3 evaluation):
  {for each reference file: filename, line count, and content}
  {if no references were generated: "No reference files"}
```

**Decision logic**:
- Grade A → proceed to Step 5
- Grade B → re-invoke rashomon:skill-creator with reviewer's `actionItems` and `patternIssues` to fix, then re-review (max 2 iterations total)
- Grade C → re-invoke rashomon:skill-creator with reviewer's `actionItems` and `patternIssues` (max 2 iterations)
- Grade C after 2 iterations → present current content with issues list, let user decide

Present the final grade and any remaining notes to user.

## Step 5: User Review and Write

1. Display the complete SKILL.md content in a fenced code block (full frontmatter and body)
2. If references/ files were generated, display each file's content in separate fenced code blocks
3. Use AskUserQuestion: "Please review the skill content above. Is there anything you'd like to change?"
4. If revision requested: collect specific feedback, re-run Step 3 with adjustments
5. Upon approval, write to target location:
   - Default: `.claude/skills/{name}/SKILL.md`
   - If references exist: `.claude/skills/{name}/references/`

**Phase A complete. Proceed to eval.md for Phase B.**

## Phase B Handoff Data

Phase A must pass the following to Phase B (eval.md). The orchestrator carries these in context:

| Data | Source | Purpose |
|------|--------|---------|
| Skill name | Round 5 | `--skill-name` parameter |
| Source skill directory | Step 5 write location | Worktree copy source |
| User phrases | Round 3 (both categories) | Reference material for trigger query generation |
| Trigger scenarios | Round 3 | Reference material for trigger query generation |

## Completion Criteria

- [ ] No naming conflict with existing skills (or user confirmed override)
- [ ] Project-specific value validated in Round 2
- [ ] User phrases collected and classified in Round 3 (at least 1 skill-dependent)
- [ ] Skill name confirmed by user
- [ ] rashomon:skill-creator returned valid output
- [ ] rashomon:skill-reviewer returned grade A (or B issues fixed)
- [ ] User approved final content
- [ ] File written to target location
