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

### Round 3: Scope, Triggers, and Held-Out Test Tasks

Present these questions as plain text and wait for the user's response:
- When should this skill be activated? List 3-5 concrete scenarios
- What does this skill explicitly cover vs. what it leaves out?
- What complete requests does your team actually send when asking for this work? Provide at least two skill-dependent requests verbatim. They remain outside description authoring until selected for trigger/effectiveness testing.

After collecting responses, classify each request into two categories:

| Category | Definition | Example |
|----------|-----------|---------|
| **Skill-dependent** | Cannot be completed correctly without the skill's knowledge; pattern-copying existing code would produce an incorrect or incomplete result | "Review the retry behavior in `fetchOrder` against our service policy and fix any violations." |
| **Pattern-copyable** | Can be completed by reading and copying existing code patterns | "Add a `fetchOrder` function matching `fetchUser`." |

If the requests are pattern-copyable, inform the user: "These tasks can be completed by copying existing code. Can you provide requests that require the hidden rules this skill encodes?" Ensure at least two complete skill-dependent requests exist before proceeding.

**Phase B handoff**: Store both categories verbatim. Keep at least two skill-dependent requests out of description examples and authoring prompts. Phase B uses one directly and reserves another if a failed query must later become authoring evidence.

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
  Existing generated content: {current full SKILL.md and references on repair, or "None"}
  Raw knowledge: {content from Round 4}
  Trigger scenarios: {scenarios from Round 3}
  User phrases: {non-held-out team phrases from Round 3}
  Scope: {coverage and boundaries from Round 3}
  Decision criteria: {rules from Round 4}
  Practical artifacts: {files, failures, PRs from Round 4, if provided}
  Project-specific value: {details from Round 2}
  Current review: {skill-reviewer output on repair, or "None"}
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

  Previous review (on re-review):
  {prior skill-reviewer output, or "None"}

  Review resolutions (on re-review):
  {skill-creator reviewResolutions, or "None"}
```

**Decision logic**:
- Grade A/B → proceed to Step 5 and present remaining Grade B findings as optional notes
- Grade C → ask rashomon:skill-creator to resolve each finding by `findingId` as `apply`, `decline`, or `user_decision`
- `apply` → revise and re-review; `decline` → re-review with evidence; `user_decision` → ask the user
- A reviewer may maintain a declined finding only with new correctness or verifiability evidence; repeated preference is non-blocking
- Grade C after 2 repair/re-review iterations → present current content with remaining findings, let user decide

Present the final grade and any remaining notes to user.

## Step 5: User Review and Write

1. Display the complete SKILL.md content in a fenced code block (full frontmatter and body)
2. If references/ files were generated, display each file's content in separate fenced code blocks
3. Use AskUserQuestion: "Please review the skill content above. Is there anything you'd like to change?"
4. If revision requested: collect specific feedback, re-run Step 3 with adjustments
5. Upon approval, write to target location:
   - Default: `.claude/skills/{name}/SKILL.md`
   - If references exist: `.claude/skills/{name}/references/`
6. Compute and record the fingerprint of the complete written skill directory for Phase B.

**Phase A complete. Proceed to eval.md for Phase B.**

## Phase B Handoff Data

Phase A must pass the following to Phase B (eval.md). The orchestrator carries these in context:

| Data | Source | Purpose |
|------|--------|---------|
| Skill name | Round 5 | `--skill-name` parameter |
| Source skill directory | Step 5 write location | Worktree copy source |
| Source directory fingerprint | Step 6 | Verify with-skill installation identity |
| Held-out test requests | Round 3 (verbatim, skill-dependent) | Direct input for trigger and effectiveness checks |
| Other user phrases | Round 3 | Description authoring context; excluded from test selection |
| Trigger scenarios | Round 3 | Validate that the held-out request is in scope |

## Completion Criteria

- [ ] No naming conflict with existing skills (or user confirmed override)
- [ ] Project-specific value validated in Round 2
- [ ] Complete user requests collected and classified in Round 3 (at least two held-out skill-dependent requests)
- [ ] Skill name confirmed by user
- [ ] rashomon:skill-creator returned valid output
- [ ] rashomon:skill-reviewer returned grade A (or B issues fixed)
- [ ] User approved final content
- [ ] File written to target location
