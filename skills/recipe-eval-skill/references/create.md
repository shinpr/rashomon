# Creation Mode Procedure

Steps for creating a new skill through interactive dialog and optimization.

## Step 1: Pre-flight Check

1. Glob existing skills: `.claude/skills/*/SKILL.md`, `skills/*/SKILL.md`
2. If user's topic matches an existing skill name: inform user and confirm whether to proceed or modify existing
3. List existing skill names for user awareness

## Step 2: Collect Skill Knowledge

Collect information in 3 rounds of dialog.

**Round 1: Skill Essence**
- What domain knowledge does this skill encode? (1-2 sentences)
- What is the primary goal when this skill is applied? (e.g., "ensure type safety", "standardize test patterns")

**Round 2: Scope and Triggers**
- When should this skill be activated? List 3-5 concrete scenarios (e.g., "when writing unit tests", "when reviewing PR for security")
- What does this skill explicitly NOT cover? (scope boundary)

**Round 3: Decision Criteria and Evidence**
- What are the concrete rules or criteria? (the core knowledge to encode)
- Any examples of good/bad patterns?
- Any external references or standards this skill is based on?
- **Practical artifacts** (strongly recommended):
  - Existing implementation files that demonstrate the desired patterns
  - Past failures or bugs caused by not following these patterns
  - Related PRs, issues, or runbooks that encode this knowledge
  - Conversation logs where you've repeatedly explained these rules to others

  These artifacts ground the skill in real-world usage rather than abstract rules. Prompt the user: "Do you have any existing files, past failures, or documentation that demonstrate these patterns? Even a single concrete example helps more than abstract rules."

## Step 3: Determine Name and Structure

1. Derive skill name in gerund/noun form:
   - Examples: `coding-standards`, `typescript-rules`, `implementation-approach`
2. Estimate size based on collected content volume
3. Present name and structure to user for confirmation

## Step 4: Generate Skill Content

Invoke **skill-creator** agent in creation mode:

```yaml
Input:
  mode: creation
  skillName: {name from Step 3}
  rawKnowledge: {content from Round 3}
  triggerScenarios: {scenarios from Round 2}
  scope: {coverage and boundaries from Round 2}
  decisionCriteria: {rules from Round 3}
  practicalArtifacts: {files, failures, PRs, examples from Round 3, if provided}
```

skill-creator reads `prompt-optimization/references/skills.md` and applies:
- BP-001~008 transforms (P1 > P2 > P3)
- 9 editing principles
- Progressive disclosure structure
- Standard section order

## Step 5: Review Generated Content

Invoke **skill-reviewer** agent:

```yaml
Input:
  skillContent: {skill-creator output}
  reviewMode: creation
```

**Decision logic**:
- Grade A or B → proceed to Step 6
- Grade C → re-invoke skill-creator with reviewer's `actionItems` and `patternIssues` appended as additional context (max 2 iterations)
- Grade C after 2 iterations → present current content with issues list, let user decide

## Step 6: User Review and Write

1. Present generated SKILL.md content to user for final approval
2. Ask: "Does this skill capture the knowledge and criteria you described?"
3. If revision requested: collect specific feedback, re-run Step 4 with adjustments
4. Upon approval, write to target location:
   - Default: `.claude/skills/{name}/SKILL.md`
   - If references exist: `.claude/skills/{name}/references/` for extracted files
5. If reviewer noted remaining B-grade items, present them as optional future improvements

**Phase A complete. Proceed to eval.md for Phase B.**

## Completion Criteria

- [ ] No naming conflict with existing skills (or user confirmed override)
- [ ] Skill knowledge collected through 3 rounds of dialog
- [ ] Skill name confirmed by user
- [ ] skill-creator agent returned valid output
- [ ] skill-reviewer agent returned grade A or B
- [ ] User approved final content
- [ ] File written to target location
