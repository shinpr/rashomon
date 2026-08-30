---
name: prompt-optimization
description: Improves LLM-facing context while preserving intent, execution boundaries, and proportional work. Use when creating or reviewing prompts, agent definitions, skill definitions, or other instructions for an LLM.
---

# Prompt Optimization Skill

## Purpose

Improve prompts while preserving user intent.

## Core Principles

1. **Procedural Gates**: Complete analysis, optimization, and balance in order. Each phase has observable pass conditions that control the next transition.
2. **Intent Preservation**: Record the original requirements before changing wording, structure, context, constraints, or examples.
3. **Necessary and Sufficient Context**: Include the information needed for a decision, action, or verification result. Condense or omit information that does not affect one of them.
4. **Minimal Sufficient Work**: Classify discovered possibilities as candidates. Add work only when it changes the outcome, protects a required boundary, serves a real consumer, or supplies necessary proof.
5. **Traceable Changes**: Connect every change to a finding or project-specific source.
6. **Self-Contained Execution**: Require no temporary artifacts or additional agents.

## Required References

Load references at the phase where their rules become necessary:

| Phase | Condition | Required reference |
|---|---|---|
| Analysis | Every prompt | `references/patterns.yaml` |
| Analysis | Target is a SKILL.md, agent, or skill reference | `references/skills.md` |
| Balance | Every prompt | `references/execution-quality.yaml` |

Record the loaded path and covered rule IDs in the phase's `reference_coverage`. A phase passes only when its required references and rule coverage are present.

## Output Mode

Select the output mode before analysis. An explicit `output_mode` of `interactive` or `machine` takes priority; for any other value, ask the caller to choose one. When it is absent, use Machine mode only if the caller explicitly requests the `Machine Output Contract` as the response format; otherwise use Interactive mode. Apply the same rule to human and LLM callers.

Keep `output_mode` outside the target prompt and `analysis.original_prompt`.

## Pattern Detection

Evaluate every pattern and record `issue`, `already_satisfied`, or `not_applicable`.

| Priority | ID | Pattern | Decision goal |
|---|---|---|---|
| P1 | BP-001 | Negative Instructions | Lead with the required behavior; retain explicit prohibitions for narrow irreversible boundaries |
| P1 | BP-002 | Vague Instructions | Resolve an outcome-relevant ambiguity with the least-restrictive sufficient criterion |
| P1 | BP-003 | Missing Output Format | Define the shape needed by the output consumer |
| P1 | BP-009 | Unbounded Work Generation | Prevent technically valid possibilities from becoming unnecessary work |
| P2 | BP-004 | Unstructured Prompt | Make priority and relationships visible when structure reduces ambiguity |
| P2 | BP-005 | Missing or Excess Context | Supply decision-sufficient context without distractors or duplication |
| P2 | BP-006 | Missing or Excess Procedural Control | Keep required gates without prescribing reversible routes |
| P3 | BP-007 | Unnecessary or Biased Examples | Use examples only for non-obvious mappings, then control their bias |
| P3 | BP-008 | Missing Uncertainty Handling | Define evidence, escalation, and stopping behavior for unresolved inputs |

## Gated 3-Step Flow

Maintain one complete phase-state object in the current invocation. Complete each phase and its gate before generating the next phase; use the transition table as the control rule. Serialize the object only in Machine mode.

### Step 1: Analysis

1. Load the analysis references required for the target type.
2. Preserve the original prompt verbatim.
3. Record the prompt's intended outcome and requirements that later phases must preserve.
4. Evaluate BP-001 through BP-009. Record every distinct issue in `findings` with a unique `finding_id`, pattern, severity, location, and quoted evidence. A BP-002 finding represents one decision required by the intended outcome whose plausible interpretations would materially change correctness, requested scope, downstream usability, or verification.
5. Record missing inputs under `unresolved_inputs`.

`analysis_gate` passes when:

- all required analysis references are covered;
- BP-001 through BP-009 each have one summary whose `finding_ids` match its findings;
- every distinct issue has one finding with evidence, location, pattern, and severity;
- preservation requirements are explicit; and
- no unresolved input prevents a faithful optimization.

### Step 2: Optimization

Start this step when `analysis_gate.status` is `pass`.

1. Resolve every finding as `applied` or `skipped` with a reason. For BP-002, choose the least-restrictive clarification that supplies the required precision and base the reason on its precision contribution and constraint cost.
2. Apply Structural and Context Addition changes that improve task execution.
3. Consolidate redundant changes and preserve requirements recorded in Step 1.
4. Produce the candidate optimized prompt.

`optimization_gate` passes when:

- every finding has exactly one resolution;
- every change traces to a finding or named project source;
- all preservation requirements remain represented;
- added constraints remove a real ambiguity or protect a real requirement;
- added obligations affect the outcome, a required boundary, a real consumer, or necessary proof; and
- every applied BP-002 clarification identifies an observable precision contribution and preserves the valid solutions allowed by the original intent.

### Step 3: Balance

Start this step when `optimization_gate.status` is `pass`.

1. Load `references/execution-quality.yaml`.
2. Evaluate intent preservation, decision sufficiency, information density, constraint necessity, work proportionality, and traceability.
3. Apply balance adjustments and record each adjustment.
4. Produce the final prompt and final status.

`balance_gate` passes when every applicable balance check has evidence and no blocking check remains. Use `original_sufficient` when the analysis found no beneficial change.

## State Transitions

| Gate result | Required transition |
|---|---|
| `pass` | Populate the next phase and its gate |
| `blocked` | Keep later workflow phases and their gates `null`, set `result.status` to `blocked`, and format the result in the selected output mode |
| Final balance `pass` with changes | Set `result.status` to `optimized` |
| Final balance `pass` without changes | Set `result.status` to `original_sufficient` |

## Interactive Output Contract

Format the user-facing result by status:

- For `optimized`, return `## Final Prompt` with the optimized prompt, followed by `## Changes` with one bullet per applied change and its reason.
- For `original_sufficient`, return `## Final Prompt` with the original prompt, followed by `## Changes` stating that no beneficial change was found and the original is already sufficient.
- For `blocked`, return only `## Required Input` with one bullet per missing item needed to continue.

## Machine Output Contract

In Machine mode, return exactly one valid JSON object in this key order. Populate phases sequentially; later phases remain `null` until their preceding gate passes.

```json
{
  "analysis": {
    "original_prompt": "verbatim input",
    "target_type": "general_prompt | skill_content",
    "intended_outcome": "observable outcome",
    "reference_coverage": [{"path": "references/patterns.yaml", "rule_ids": ["BP-001", "BP-002", "BP-003", "BP-004", "BP-005", "BP-006", "BP-007", "BP-008", "BP-009"]}],
    "pattern_coverage": {
      "BP-001": {"status": "issue | already_satisfied | not_applicable", "finding_ids": ["F-001"], "evidence": ["summary evidence or applicability reason"]},
      "BP-002": {"status": "issue | already_satisfied | not_applicable", "finding_ids": ["F-002", "F-003"], "evidence": ["summary evidence or applicability reason"]},
      "BP-003": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-004": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-005": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-006": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-007": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-008": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]},
      "BP-009": {"status": "issue | already_satisfied | not_applicable", "finding_ids": [], "evidence": ["summary evidence or applicability reason"]}
    },
    "findings": [{"finding_id": "F-001", "pattern_id": "BP-001", "severity": "P1", "location": "section or line", "evidence": ["verbatim issue evidence"]}, {"finding_id": "F-002", "pattern_id": "BP-002", "severity": "P1", "location": "first vague instruction", "evidence": ["verbatim evidence"]}, {"finding_id": "F-003", "pattern_id": "BP-002", "severity": "P1", "location": "second vague instruction", "evidence": ["verbatim evidence"]}],
    "preservation_requirements": ["requirement"],
    "unresolved_inputs": []
  },
  "analysis_gate": {"status": "pass | blocked", "missing": []},
  "optimization": {"finding_resolutions": [{"finding_id": "F-001", "decision": "applied | skipped", "reason": "reason", "change": "change or null", "source": "finding | project path"}], "candidate_prompt": "optimized candidate"},
  "optimization_gate": {"status": "pass | blocked", "missing": []},
  "balance": {
    "reference_coverage": [{"path": "references/execution-quality.yaml", "rule_ids": ["intent_preservation", "decision_sufficiency", "information_density", "constraint_necessity", "work_proportionality", "traceability"]}],
    "checks": [
      {"check_id": "intent_preservation", "status": "pass | blocked", "evidence": "comparison evidence"},
      {"check_id": "decision_sufficiency", "status": "pass | blocked", "evidence": "execution evidence"},
      {"check_id": "information_density", "status": "pass | blocked", "evidence": "context evidence"},
      {"check_id": "constraint_necessity", "status": "pass | blocked", "evidence": "constraint trace"},
      {"check_id": "work_proportionality", "status": "pass | blocked", "evidence": "obligation effect"},
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

### BP-006: Procedural Control

Keep gates for true dependencies, authority, irreversible actions, machine-consumed contracts, and completion proof. For reversible choices, state the purpose, relevant evidence, and selection criteria without prescribing the route.

### BP-007: Examples

Default to concise rules or consumer-required output shapes for generally known behavior. Add an example when it conveys a domain-, product-, or organization-specific mapping, a non-obvious exception, or a boundary that a rule cannot express. Connect every example to the ambiguity it removes and keep the smallest set that covers those ambiguities.

### BP-009: Work Generation

Treat discovered findings and technically valid possibilities as candidates. Keep only work required by the outcome, a boundary, a real consumer, or necessary proof; allow evidence-backed no-change, reuse, and decline; stop when the intended outcome is observable.

### Code and Repository Tasks

When the target requires a code or repository change:

- Treat source, tests, configuration, interfaces, and callers as project artifacts that can supply required decisions.
- Derive compatibility and verification criteria from the repository's existing contracts and workflows.
- Require evidence from the relevant established checks before claiming completion.

## Improvement Classification

| Classification | Definition | Interpretation |
|---|---|---|
| **Structural** | Changes to organization, criteria, gates, or output shape | Prompt writing technique |
| **Context Addition** | Project-specific information added from a traceable source | Information advantage |
| **Expressive** | Different phrasing with equivalent executable meaning | Neutral |
| **Variance** | Difference without an attributable requirement or execution effect | Original prompt sufficient |

## References

- `references/patterns.yaml` - Detailed BP-001 through BP-009 decision rules
- `references/execution-quality.yaml` - Balance checks and comparison criteria
- `references/skills.md` - Skill-specific BP adaptations and progressive disclosure
