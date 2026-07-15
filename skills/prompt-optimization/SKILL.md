---
name: prompt-optimization
description: Analyzes and optimizes prompts using BP-001~008 patterns and a gated 3-step flow. Use when "optimize this prompt", "review prompt quality", "analyze prompt issues", or creating/reviewing rashomon skill content.
---

# Prompt Optimization Skill

## Purpose

Improve prompts while preserving user intent. Execute the workflow in the current invocation and keep intermediate state in returned JSON so it remains portable across callers and environments.

## Core Principles

1. **Procedural Gates**: Complete analysis, optimization, and balance in order. Each phase has observable pass conditions that control the next transition.
2. **Intent Preservation**: Record the original requirements before changing wording, structure, context, constraints, or examples.
3. **Necessary and Sufficient Context**: Include the information needed for a decision, action, or verification result. Condense or omit information that does not affect one of them.
4. **Traceable Changes**: Connect every change to a finding or project-specific source.
5. **Portable State**: Represent phase state in the response JSON. The protocol requires no temporary artifacts or additional agents.

## Required References

Load references at the phase where their rules become necessary:

| Phase | Condition | Required reference |
|---|---|---|
| Analysis | Every prompt | `references/patterns.yaml` |
| Analysis | Target is a SKILL.md, agent, or skill reference | `references/skills.md` |
| Balance | Every prompt | `references/execution-quality.yaml` |

Record the loaded path and covered rule IDs in the phase's `reference_coverage`. A phase passes only when its required references and rule coverage are present.

## Pattern Detection

Evaluate every pattern and record `issue`, `already_satisfied`, or `not_applicable`.

| Priority | ID | Pattern | Decision goal |
|---|---|---|---|
| P1 | BP-001 | Negative Instructions | Lead with the required behavior; retain explicit prohibitions for narrow irreversible boundaries |
| P1 | BP-002 | Vague Instructions | Replace delegated guesses with observable criteria or decision rules |
| P1 | BP-003 | Missing Output Format | Define the shape needed by the output consumer |
| P2 | BP-004 | Unstructured Prompt | Make priority and relationships visible when structure reduces ambiguity |
| P2 | BP-005 | Missing or Excess Context | Supply decision-sufficient context without distractors or duplication |
| P2 | BP-006 | Missing Procedural Gates | Split sequential work into steps with completion evidence |
| P3 | BP-007 | Unnecessary or Biased Examples | Use examples only for non-obvious mappings, then control their bias |
| P3 | BP-008 | Missing Uncertainty Handling | Define evidence, escalation, and stopping behavior for unresolved inputs |

## Gated 3-Step Flow

Build one JSON object in **Output Contract** key order. Complete each phase and its gate before generating the next phase; use the transition table as the control rule.

### Step 1: Analysis

1. Load the analysis references required for the target type.
2. Preserve the original prompt verbatim.
3. Record the prompt's intended outcome and requirements that later phases must preserve.
4. Evaluate BP-001 through BP-008. Record every distinct issue in `findings` with a unique `finding_id`, pattern, severity, location, and quoted evidence.
5. Record missing inputs under `unresolved_inputs`.

`analysis_gate` passes when:

- all required analysis references are covered;
- BP-001 through BP-008 each have one summary whose `finding_ids` match its findings;
- every distinct issue has one finding with evidence, location, pattern, and severity;
- preservation requirements are explicit; and
- no unresolved input prevents a faithful optimization.

### Step 2: Optimization

Start this step when `analysis_gate.status` is `pass`.

1. Resolve every finding as `applied` or `skipped` with a reason.
2. Apply Structural and Context Addition changes that improve task execution.
3. Consolidate redundant changes and preserve requirements recorded in Step 1.
4. Produce the candidate optimized prompt.

`optimization_gate` passes when:

- every finding has exactly one resolution;
- every change traces to a finding or named project source;
- all preservation requirements remain represented; and
- added constraints remove a real ambiguity or protect a real requirement.

### Step 3: Balance

Start this step when `optimization_gate.status` is `pass`.

1. Load `references/execution-quality.yaml`.
2. Evaluate intent preservation, decision sufficiency, information density, constraint necessity, and traceability.
3. Apply balance adjustments and record each adjustment.
4. Produce the final prompt and final status.

`balance_gate` passes when every applicable balance check has evidence and no blocking check remains. Use `original_sufficient` when the analysis found no beneficial change.

## State Transitions

| Gate result | Required transition |
|---|---|
| `pass` | Populate the next phase and its gate |
| `blocked` | Keep later workflow phases and their gates `null`, set `result.status` to `blocked`, and return the JSON |
| Final balance `pass` with changes | Set `result.status` to `optimized` |
| Final balance `pass` without changes | Set `result.status` to `original_sufficient` |

## Output Contract

Return valid JSON in this key order. Populate phases sequentially; later phases remain `null` until their preceding gate passes.

```json
{
  "protocol_version": "1.2",
  "analysis": {
    "original_prompt": "verbatim input",
    "target_type": "general_prompt | skill_content",
    "intended_outcome": "observable outcome",
    "reference_coverage": [{"path": "references/patterns.yaml", "rule_ids": ["BP-001", "BP-002", "BP-003", "BP-004", "BP-005", "BP-006", "BP-007", "BP-008"]}],
    "pattern_coverage": {
      "BP-001": {"status": "issue | already_satisfied | not_applicable", "finding_ids": ["F-001"], "evidence": ["summary evidence or applicability reason"]},
      "BP-002": {"status": "issue | already_satisfied | not_applicable", "finding_ids": ["F-002", "F-003"], "evidence": ["summary evidence or applicability reason"]},
      "BP-003": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-004": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-005": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-006": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-007": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-008": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]}
    },
    "findings": [{"finding_id": "F-001", "pattern_id": "BP-001", "severity": "P1", "location": "section or line", "evidence": ["verbatim issue evidence"]}, {"finding_id": "F-002", "pattern_id": "BP-002", "severity": "P1", "location": "first vague instruction", "evidence": ["verbatim evidence"]}, {"finding_id": "F-003", "pattern_id": "BP-002", "severity": "P1", "location": "second vague instruction", "evidence": ["verbatim evidence"]}],
    "preservation_requirements": ["requirement"],
    "unresolved_inputs": []
  },
  "analysis_gate": {"status": "pass | blocked", "missing": []},
  "optimization": {"finding_resolutions": [{"finding_id": "F-001", "decision": "applied | skipped", "reason": "reason", "change": "change or null", "source": "finding | project path"}], "candidate_prompt": "optimized candidate"},
  "optimization_gate": {"status": "pass | blocked", "missing": []},
  "balance": {
    "reference_coverage": [{"path": "references/execution-quality.yaml", "rule_ids": ["intent_preservation", "decision_sufficiency", "information_density", "constraint_necessity", "traceability"]}],
    "checks": [
      {"check_id": "intent_preservation", "status": "pass | blocked", "evidence": "comparison evidence"},
      {"check_id": "decision_sufficiency", "status": "pass | blocked", "evidence": "execution evidence"},
      {"check_id": "information_density", "status": "pass | blocked", "evidence": "context evidence"},
      {"check_id": "constraint_necessity", "status": "pass | blocked", "evidence": "constraint trace"},
      {"check_id": "traceability", "status": "pass | blocked", "evidence": "finding or source mapping"}
    ],
    "adjustments": []
  },
  "balance_gate": {"status": "pass | blocked", "missing": []},
  "result": {"status": "optimized | original_sufficient | blocked", "final_prompt": "prompt or null"}
}
```

Field types are fixed: `analysis` and `analysis_gate` are objects; optimization fields become objects only after analysis passes; balance fields become objects only after optimization passes. Otherwise later phases are `null`. `result.final_prompt` is a string for `optimized` or `original_sufficient`, and `null` for `blocked`.

Example of an analysis-blocked transition:

```json
{
  "protocol_version": "1.2",
  "analysis": {"original_prompt": "verbatim input", "target_type": "skill_content", "intended_outcome": "observable outcome", "reference_coverage": [], "pattern_coverage": {}, "findings": [], "preservation_requirements": [], "unresolved_inputs": ["required skill reference unavailable"]},
  "analysis_gate": {"status": "blocked", "missing": ["references/skills.md"]},
  "optimization": null,
  "optimization_gate": null,
  "balance": null,
  "balance_gate": null,
  "result": {"status": "blocked", "final_prompt": null}
}
```

## Conditional Rules

### BP-001: Negative Instructions

State the desired action or allowed state first. Preserve an explicit prohibition when the violation is an irreversible operational action, the caller cannot normally recover it, and a positive-only rewrite would blur the boundary. Pair the prohibition with the safe alternative and the condition that authorizes crossing the boundary.

### BP-004: Structure

Add structure when the prompt contains multiple instructions, sequential dependencies, or implicit section boundaries. Preserve lightweight prose for a single clear action.

### BP-005: Context

For each context item, identify the decision, action, or verification it controls. Add missing items that change one of those outcomes. Condense duplicated items and items with no downstream effect.

### BP-006: Decomposition

Use ordered steps when the task has sequential dependencies or when an early result must be verified before later work. Give each step observable completion evidence and a next-state rule.

### BP-007: Examples

Default to instructions or schemas for generally known behavior. Add an example when it conveys a domain-, product-, or organization-specific mapping, a non-obvious exception, or a boundary that a schema cannot express. Connect every example to the ambiguity it removes and keep the smallest set that covers those ambiguities.

## Improvement Classification

| Classification | Definition | Interpretation |
|---|---|---|
| **Structural** | Changes to organization, criteria, gates, or output shape | Prompt writing technique |
| **Context Addition** | Project-specific information added from a traceable source | Information advantage |
| **Expressive** | Different phrasing with equivalent executable meaning | Neutral |
| **Variance** | Difference without an attributable requirement or execution effect | Original prompt sufficient |

## References

- `references/patterns.yaml` - Detailed BP-001 through BP-008 decision rules
- `references/execution-quality.yaml` - Balance checks and comparison criteria
- `references/skills.md` - Skill-specific BP adaptations and progressive disclosure
