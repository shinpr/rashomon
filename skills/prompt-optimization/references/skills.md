# Skill-Specific Optimization

Supplementary criteria for applying prompt optimization patterns (BP-001~009) to Claude Code skill files (SKILL.md, agents, references). Read this file when creating, reviewing, or optimizing skills.

## BP Patterns in Skill Context

The 9 BP patterns from the parent SKILL.md apply to skill content with these adaptations.

### Two roles of skill content

Skill content serves two distinct roles. Apply BP patterns accordingly:

| Role | Description | BP application |
|------|-------------|----------------|
| **LLM instruction** | Directs the LLM's own judgment and behavior | Apply BP patterns directly |
| **Output pattern guidance** | Examples or templates that shape what the LLM produces for a downstream consumer | Apply BP to the instruction framing rather than individual example values. Consumer-required parameters remain valid when they control downstream interpretation or acceptance. |

### Pattern interpretations

| Pattern | Skill-Specific Interpretation |
|---------|-------------------------------|
| BP-001 Negative Instructions | Lead with the desired action or allowed state. Preserve a narrow explicit prohibition only when violation is an irreversible operational action, the caller cannot normally recover it, and a positive-only rewrite would blur the boundary. Pair it with the safe alternative and authorization condition. Rewrite quality policies and scoring rules as positive criteria because their outputs remain reviewable. |
| BP-002 Vague Instructions | Record a finding only when a vague term leaves one decision required by the intended outcome and plausible interpretations would materially change execution or verification. Choose the least-restrictive sufficient criterion: the measurable criterion or if-then rule that supplies the required precision while excluding the fewest valid behaviors. Record outcome-relevant precision contribution and constraint cost in the resolution reason. Expressions resolved unambiguously from input context are already satisfied. |
| BP-003 Missing Output Format | Every process or methodology section defines the output contract required by its consumer. |
| BP-004 Unstructured Content | Apply standard section order (see below). Skip restructuring if skill is under 30 lines and covers a single topic. |
| BP-005 Missing or Excess Context | Include the context needed for a decision, action, or verification result. Define project-specific terms and name source paths. Baseline technical knowledge needs no explanation. Condense duplicated background and content with no downstream effect. |
| BP-006 Procedural Control | Keep gates for true dependencies, authority, irreversible actions, machine-consumed contracts, and completion proof. For reversible choices, provide purpose, evidence, and selection criteria without prescribing the route. |
| BP-007 Unnecessary or Biased Examples | Default to concise rules or consumer-required output shapes for generally known behavior. Add the smallest example set that communicates organization-, product-, or domain-specific mappings, non-obvious exceptions, or boundaries that a rule cannot express. Map every example to the ambiguity it removes. |
| BP-008 Missing Uncertainty Handling | Classify evidence as observed, inferred, or unknown. Add escalation criteria and explicit stopping conditions when an unknown blocks the next transition. |
| BP-009 Unbounded Work Generation | Treat discovered considerations as candidates. Retain only work required by the outcome, a boundary, a real consumer, or necessary proof; allow no-change, reuse, and evidence-backed decline. |

## 10 Editing Principles

Measurable quality criteria for skill content. Each principle includes a pass/fail test.

| # | Principle | Pass Criteria | Fail Example |
|---|-----------|---------------|--------------|
| 1 | Context efficiency | Every sentence supplies non-baseline knowledge, a decision rule, a required boundary, or execution evidence. | Restates baseline behavior without a supplied failure, review finding, or project requirement showing an execution effect |
| 2 | Deduplication | No concept explained twice at the same abstraction level within the skill or across skills. Mentions at different structural roles, such as classification and execution, are distinct | The same rule appears in multiple sections without a distinct role |
| 3 | Grouping | Related criteria appear in one section to minimize read operations | One policy is scattered across unrelated sections |
| 4 | Measurability | Criteria name observable evidence, deterministic decision rules, or justified thresholds | A quality label appears without an observable condition |
| 5 | Positive form | Instructions state the desired action or allowed state | An instruction names only a forbidden state |
| 6 | Consistent notation | Uniform heading levels, list styles, table formats | Mix of `-`, `*`, `1.` in same context |
| 7 | Explicit prerequisites | Project-specific and non-baseline prerequisites are stated or linked; baseline technical knowledge is left concise | Uses an internal acronym without defining or linking it |
| 8 | Priority ordering | Most important items first, exceptions last | Edge cases before common patterns |
| 9 | Scope boundaries | Explicit coverage: what this skill addresses vs references to other skills | Overlapping guidance with no cross-reference |
| 10 | Work proportionality | Every required artifact, test, gate, or decision changes the outcome, a boundary, a consumer result, or necessary proof | Requires all findings or technically valid improvements to be implemented |

## Progressive Disclosure

Skills implement a 3-tier disclosure architecture. Each tier loads only when needed, preserving context window budget.

### Compression Budget

The targets below are intentionally smaller than platform limits. Meet them by removing dispensable content; references retain only necessary conditional detail.

Before splitting content:

1. Remove baseline knowledge, duplication, and corrective rules not tied to an observed recurring failure or required boundary.
2. Replace exhaustive branches with purpose, evidence, and selection criteria.
3. Remove examples without a non-obvious mapping or exception.
4. Move repeatable deterministic operations to scripts.
5. Extract only remaining conditional detail whose load condition and decision effect are explicit.

References retain content that passes the same necessity test.

### Tier 1: Metadata (description)

Loaded at startup for ALL skills. Shared 15,000-character budget across all loaded skills.

**Core principle**: The description supplies the evidence used to select a skill. It must express the user intent and project-specific value that distinguish this skill from baseline model knowledge; it is not a human-oriented table of contents.

**Requirements**:
- Third-person, verb-first: "Evaluates X against Y" (NOT "This skill evaluates...")
- Focus on user intent, not implementation: describe what the user is trying to achieve, not the skill's internal mechanics
- Include a "Use when:" trigger using the actual phrases callers use
- Explicitly list contexts where the skill applies, including cases where the user does not name the domain directly
- Target ~200 characters (hard limit: 1024)
- Template: `{Verb}s {what} using {project-specific criteria/patterns}. Use when {user phrases that trigger this skill}.`

**Description quality checklist**:
- [ ] Contains project-specific terms, entities, or decision rules that differentiate from general LLM knowledge
- [ ] Uses phrases the team actually says when requesting this kind of work
- [ ] Focuses on user intent and caller situations rather than skill internals
- [ ] A skill covering only general knowledge that the LLM already knows indicates the skill needs project-specific content, or is unnecessary

**Name field**:
- Max 64 characters, lowercase letters/numbers/hyphens only
- Gerund form preferred

### Tier 2: SKILL.md Body

Loaded when Claude determines the skill is relevant to the current task.

**Requirements**:
- Body under 500 lines (hard limit), under 250 lines (target). Above the target passes only when removing a retained section would change a non-baseline decision, required boundary, consumer contract, or observed recurring failure
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
- After compression, SKILL.md over 400 lines must split remaining conditional detail; splitting does not satisfy the 250-line necessity test
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
| A | 0 P1, 0 P2 issues, 9+ principles pass | Ready for use |
| B | 0 P1, ≤2 P2 issues, 7+ principles pass | Acceptable with noted improvements |
| C | Any P1 OR >2 P2 OR <7 principles pass | Revision required |

### Review Flow

**Step 1: Pattern Scan**
1. Scan for each BP pattern (BP-001 through BP-009) in skill context
2. Record: stable finding ID, pattern ID, severity, location, original text
3. Evaluate against 10 editing principles
4. Count total lines, estimate size category

**Step 2: Evaluate and Grade**
1. Keep unresolved issues in `findings` and evidence-backed accepted declines in `acceptedDeclines`. Accepted declines contribute zero to issue counts and principle results.
2. Count P1 and P2 findings
3. Count only `pass` principle results
4. Check cross-skill overlap (Glob: `.claude/skills/*/SKILL.md`, `~/.claude/skills/*/SKILL.md`)
5. Balance assessment:
   - Over-optimization: Excessive constraints or generated obligations; content above the 250-line target without completed compression
   - Lost expertise: Domain knowledge compressed away in structured content
   - Clarity trade-off: Structure obscures main point
   - Description quality: Apply Tier 1 description quality checklist
6. Assign grade

### Review Modes

| Aspect | Creation | Modification |
|--------|----------|--------------|
| Scope | All content, comprehensive | Changed sections + regression check |
| BP scan | All 9 patterns | Focus on patterns relevant to changes |
| Cross-skill check | Full overlap scan | Verify changes did not introduce overlap |
| Extra check | — | Report issues outside change scope separately |

## Skill Generation

### Creation Flow

1. **Analyze**: Classify content (definitions, patterns, processes, criteria, examples). Detect BP issues. Estimate size.
2. **Generate**: Apply transforms P1 → P2 → P3. Structure per standard section order. Balance work proportionality and clarity.
3. **Description**: Generate per Tier 1 requirements. Use template: `{Verb}s {what} using {project-specific criteria/patterns}. Use when {user phrases}.` Apply description quality checklist.
4. **Compression and split**: Apply the compression budget first. If content still exceeds 400 lines, extract only conditional detail to `references/`. Above 250 lines, retain only sections whose removal would change a non-baseline decision, required boundary, consumer contract, or observed recurring failure.

### Modification Flow

1. **Analyze**: Parse existing SKILL.md. Identify affected sections. Note existing issues relevant to modification.
2. **Modify**: Change only affected sections. Preserve unaffected sections verbatim. Apply BP transforms to modified sections only.
3. **Description**: Re-evaluate if scope/triggers changed. Keep existing if unchanged.
4. **Compression and split**: Apply the compression budget to changed content before extracting conditional detail over 400 lines.
