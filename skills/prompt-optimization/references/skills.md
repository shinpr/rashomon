# Skill-Specific Optimization

Supplementary criteria for applying prompt optimization patterns (BP-001~008) to Claude Code skill files (SKILL.md, agents, references). Read this file when creating, reviewing, or optimizing skills.

## BP Patterns in Skill Context

The 8 BP patterns from the parent SKILL.md apply to skill content with these adaptations.

### Two roles of skill content

Skill content serves two distinct roles. Apply BP patterns accordingly:

| Role | Description | BP application |
|------|-------------|----------------|
| **LLM instruction** | Directs the LLM's own judgment and behavior | Apply BP patterns directly |
| **Output pattern guidance** | Examples/templates that shape what the LLM produces for a downstream consumer (image generation model, API, end user) | Apply BP to the instruction framing, not to individual values within examples. Increasing specificity for the downstream consumer (e.g., visual parameters instead of abstract mood words for image models) is a valid improvement even when the LLM itself understands the abstract term |

### Pattern interpretations

| Pattern | Skill-Specific Interpretation |
|---------|-------------------------------|
| BP-001 Negative Instructions | Skill instructions with "don't" increase probability of the forbidden behavior. Convert to positive directives. **Exception**: Negative form is permitted only when ALL of the following are true: (1) Violation destroys state in a single step, (2) Caller or subsequent steps cannot normally recover the outcome, (3) The constraint is an operational/procedural restriction, not a quality policy or role boundary, (4) Positive rewording would expand or blur the instruction's target scope. If any condition is no, rewrite in positive form. **Exception examples** — permitted: "Do not modify the command", "Do not add flags", "Do not execute destructive operations". **Not permitted** (rewrite in positive form): "Do not invent issues" → "Base every issue on BP patterns or 9 principles", "Do not skip P1 issues" → "Evaluate all P1 issues in every review mode", "Do not give grade A when P1 exists" → "Assign grade A only when P1 count is zero", "Do not create overlapping skills" → "Verify no scope overlap with existing skills before generating". Outputs that the caller validates, overwrites, or discards are never irreversible. Quality policies, role boundaries, scoring criteria, and general work rules are always positive form. |
| BP-002 Vague Instructions | Replace "appropriate", "good", "proper" with measurable if-then criteria or concrete thresholds. Every vague instruction forces the LLM to guess. **Skill exception**: Expressions that the LLM can resolve unambiguously from input context (e.g., "where the user left gaps" when the user's prompt is available for comparison) are not vague — they describe a deterministic operation, not a subjective judgment. |
| BP-003 Missing Output Format | Every process/methodology section must define its output structure (JSON schema, markdown template, or example). |
| BP-004 Unstructured Content | Apply standard section order (see below). Skip restructuring if skill is under 30 lines and covers a single topic. |
| BP-005 Missing Context | All assumed knowledge must be stated. Domain terms must be defined or linked to prerequisites. Add "when to use" guidance with concrete scenarios. **Skill exception**: Terms within the LLM's baseline knowledge (widely-used technical terminology, standard domain vocabulary such as photography terms, programming concepts) require no definition. Only project-specific terms, internal naming conventions, or domain jargon outside common LLM training data need explicit definition. |
| BP-006 Complex Content | Break 3+ objectives into numbered steps with checkpoints. Skip for simple reference tables or single-criteria rules. |
| BP-007 Biased Examples | Include diverse cases: happy path, edge cases, error cases, varying complexity. |
| BP-008 No Uncertainty Permission | Add escalation criteria for ambiguous cases and explicit stopping conditions. |

## 9 Editing Principles

Measurable quality criteria for skill content. Each principle includes a pass/fail test.

| # | Principle | Pass Criteria | Fail Example |
|---|-----------|---------------|--------------|
| 1 | Context efficiency | Every sentence contributes to LLM decision-making. No filler. | "This is an important skill that helps with..." |
| 2 | Deduplication | No concept explained twice at the same abstraction level within the skill or across skills. Mentions at different structural roles (e.g., classification framework vs execution detail) are not duplicates | Same error handling rules in both coding-standards and typescript-rules |
| 3 | Grouping | Related criteria in single section (minimize read operations) | Scattered error handling rules across 4 sections |
| 4 | Measurability | All criteria use if-then format or concrete thresholds | "Write clean code" without definition of clean |
| 5 | Positive form | Instructions state what to do (BP-001 applied) | "Don't use any" instead of "Use only X" |
| 6 | Consistent notation | Uniform heading levels, list styles, table formats | Mix of `-`, `*`, `1.` in same context |
| 7 | Explicit prerequisites | All assumed knowledge stated | Uses "DI" without defining Dependency Injection |
| 8 | Priority ordering | Most important items first, exceptions last | Edge cases before common patterns |
| 9 | Scope boundaries | Explicit coverage: what this skill addresses vs references to other skills | Overlapping guidance with no cross-reference |

## Progressive Disclosure

Skills implement a 3-tier disclosure architecture. Each tier loads only when needed, preserving context window budget.

### Tier 1: Metadata (description)

Loaded at startup for ALL skills. Shared 15,000-character budget across all loaded skills.

**Core principle**: The description is the agent's trigger mechanism, not a summary for humans. Agents only consult skills for tasks requiring knowledge beyond their baseline capabilities. The description must convey why this skill adds value the agent lacks.

**Requirements**:
- Third-person, verb-first: "Evaluates X against Y" (NOT "This skill evaluates...")
- Focus on user intent, not implementation: describe what the user is trying to achieve, not the skill's internal mechanics
- Include "Use when:" trigger with concrete scenarios using the actual phrases users say (e.g., "deploy to staging", "add error handling", "review this PR")
- Explicitly list contexts where the skill applies, including cases where the user does not name the domain directly
- Target ~200 characters (hard limit: 1024)
- Template: `{Verb}s {what} using {project-specific criteria/patterns}. Use when {user phrases that trigger this skill}.`

**Description quality checklist**:
- [ ] Contains project-specific terms, class names, or patterns that differentiate from general LLM knowledge
- [ ] Uses phrases the team actually says when requesting this kind of work
- [ ] Focuses on user intent ("when adding...", "when reviewing..."), not skill internals ("classifies errors into...")
- [ ] A skill covering only general knowledge that the LLM already knows indicates the skill needs project-specific content, or is unnecessary

**Name field**:
- Max 64 characters, lowercase letters/numbers/hyphens only
- Gerund form preferred: `processing-pdfs`, `analyzing-spreadsheets`

### Tier 2: SKILL.md Body

Loaded when Claude determines the skill is relevant to the current task.

**Requirements**:
- Body under 500 lines (hard limit), under 250 lines (ideal)
- First 30 lines must convey: what this does, when to use it, high-level flow (first-screen test)
- Standard section order:
  1. Context/Prerequisites
  2. Core concepts (definitions, patterns)
  3. Process/Methodology (step-by-step)
  4. Output format/Examples
  5. Quality checklist
  6. References
- Conditional sections use IF/WHEN guards (content that applies only in specific scenarios)
- Information arranged in execution order (no backward jumps)
- `disable-model-invocation: true` for recipe/orchestrator skills (excluded from auto-selection)

### Tier 3: References and Scripts

Loaded on-demand during execution, only when the agent reaches the relevant step.

**References** (`references/`):
- One level deep from SKILL.md only (no nested reference chains)
- SKILL.md over 400 lines must be split; extract large tables, examples, detailed criteria
- Content types: templates, schemas, pattern libraries, checklists, detailed criteria

**Scripts** (`scripts/`):
- Use for deterministic operations where the same code would be generated every time
- Script execution output consumes tokens; script source code does not
- Judgment criteria for script vs LLM:

| Criterion | Script | LLM |
|-----------|--------|-----|
| Same code generated every time | Yes | No |
| Failure debugging cost | High → explicit error messages | Low |
| Token savings | Significant (output only) | Minimal |
| Consistency critical | Yes | No |
| Context-dependent decisions | No | Yes |

## Quality Grading

### Grades

| Grade | Criteria | Recommendation |
|-------|----------|----------------|
| A | 0 P1, 0 P2 issues, 8+ principles pass | Ready for use |
| B | 0 P1, ≤2 P2 issues, 6+ principles pass | Acceptable with noted improvements |
| C | Any P1 OR >2 P2 OR <6 principles pass | Revision required |

### Review Flow

**Step 1: Pattern Scan**
1. Scan for each BP pattern (BP-001 through BP-008) in skill context
2. Record: pattern ID, severity, location, original text
3. Evaluate against 9 editing principles
4. Count total lines, estimate size category

**Step 2: Evaluate and Grade**
1. Count P1 and P2 issues
2. Count principles passed (pass/partial/fail)
3. Check cross-skill overlap (Glob: `.claude/skills/*/SKILL.md`, `~/.claude/skills/*/SKILL.md`)
4. Balance assessment:
   - Over-optimization: Excessive constraints for simple topic (>250 lines for simple topic)
   - Lost expertise: Domain knowledge compressed away in structured content
   - Clarity trade-off: Structure obscures main point
   - Description quality: Apply Tier 1 description quality checklist
5. Assign grade

### Review Modes

| Aspect | Creation | Modification |
|--------|----------|--------------|
| Scope | All content, comprehensive | Changed sections + regression check |
| BP scan | All 8 patterns | Focus on patterns relevant to changes |
| Cross-skill check | Full overlap scan | Verify changes did not introduce overlap |
| Extra check | — | Report issues outside change scope separately |

## Skill Generation

### Creation Flow

1. **Analyze**: Classify content (definitions, patterns, processes, criteria, examples). Detect BP issues. Estimate size.
2. **Generate**: Apply transforms P1 → P2 → P3. Structure per standard section order. Balance check (over-optimization, clarity).
3. **Description**: Generate per Tier 1 requirements. Use template: `{Verb}s {what} using {project-specific criteria/patterns}. Use when {user phrases}.` Apply description quality checklist.
4. **Split decision**: If content exceeds 400 lines, extract reference data to `references/`. Keep SKILL.md under 250 lines.

### Modification Flow

1. **Analyze**: Parse existing SKILL.md. Identify affected sections. Note existing issues relevant to modification.
2. **Modify**: Change only affected sections. Preserve unaffected sections verbatim. Apply BP transforms to modified sections only.
3. **Description**: Re-evaluate if scope/triggers changed. Keep existing if unchanged.
4. **Split decision**: If modification increases content beyond 400 lines, extract to `references/`.
