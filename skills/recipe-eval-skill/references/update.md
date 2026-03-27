# Update Mode Procedure

Steps for modifying an existing skill with targeted changes and optimization.

## Step 1: Identify Target Skill

1. Glob existing skills: `.claude/skills/*/SKILL.md`, `skills/*/SKILL.md`
2. If user specified a skill name or path: select it as target
3. If no match or ambiguous: list available skills and ask user to select
4. Read the target SKILL.md and any files in its `references/` directory
5. Present a brief summary of the skill's current scope and structure

## Step 2: Collect Modification Request

Collect the user's desired changes in 1-2 rounds:

**Round 1: Change Description**
- What changes do you want to make to this skill?
- Why is this change needed? (context helps preserve intent during modification)

**Round 2 (if needed): Clarification**
- If the request is ambiguous or touches multiple sections, ask targeted follow-up (max 2 questions)
- Confirm scope: which parts should change and which should remain unchanged

## Step 3: Analyze Current State

Invoke **skill-reviewer** agent:

```yaml
Input:
  skillContent: {current SKILL.md content}
  reviewMode: modification
```

Present key findings to user:
- Current grade
- Pre-existing issues relevant to the planned modification
- Note: pre-existing issues outside modification scope are listed but not targeted for fix

## Step 4: Execute Modification

Invoke **skill-creator** agent in modification mode:

```yaml
Input:
  mode: modification
  skillName: {target skill name}
  existingContent: {current full SKILL.md content}
  modificationRequest: {user's change description from Step 2}
  currentReview: {skill-reviewer output from Step 3}
```

skill-creator:
- Modifies only affected sections
- Preserves unaffected sections verbatim
- Applies BP transforms to modified sections only
- Returns `changesSummary` documenting each change

## Step 5: Review Modified Content

Invoke **skill-reviewer** agent:

```yaml
Input:
  skillContent: {modified SKILL.md content from Step 4}
  reviewMode: modification
```

**Decision logic**:
- Grade A or B → proceed to Step 6
- Grade C → re-invoke skill-creator in modification mode, passing reviewer's `actionItems` and `patternIssues` as additional modification context (max 2 iterations)
- Grade C after 2 iterations → present current content with issues list, let user decide

## Step 6: User Review and Write

1. Present a diff-style comparison between original and modified content
2. Present the `changesSummary` from skill-creator output
3. Ask: "Do these changes match your intent?"
4. If revision requested: collect specific feedback, return to Step 4
5. Upon approval, overwrite the target SKILL.md
   - If new references were created: write to `references/` directory
   - If existing references were modified: overwrite affected files
6. If reviewer noted remaining B-grade items, present them as optional future improvements

**Save the original SKILL.md content before overwriting — it is needed for Phase B (eval) as the "old version".**

**Phase A complete. Proceed to eval.md for Phase B.**

## Completion Criteria

- [ ] Target skill identified and read
- [ ] Modification request collected and confirmed
- [ ] Current state analyzed by skill-reviewer
- [ ] skill-creator applied targeted modifications
- [ ] skill-reviewer returned grade A or B for modified content
- [ ] User approved changes via diff review
- [ ] Modified file written to original location
- [ ] Original content preserved for Phase B eval
