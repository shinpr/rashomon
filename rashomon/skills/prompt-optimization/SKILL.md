---
name: prompt-optimization
description: Model-agnostic prompt analysis and optimization patterns based on 2025-2026 research. Use when analyzing prompts for issues or generating optimized versions. Provides 8 patterns (BP-001 through BP-008) and 3-step optimization flow.
---

# Prompt Optimization Skill

## Core Philosophy

1. **Model-Agnostic**: Patterns effective across GPT, Claude, Gemini, etc.
2. **Evidence-Based**: Based on peer-reviewed research and industry consensus
3. **Actionable**: Each detection provides specific, implementable improvements
4. **Non-Destructive**: Suggest improvements while preserving user intent and minimizing constraint creep

## Pattern Detection

### P1: Critical (Must Fix)

High confidence research evidence for negative impact.

| ID | Pattern | Research Basis |
|----|---------|----------------|
| BP-001 | Negative Instructions | Attention mechanism structural issue. 75% failure rate in ArXiv studies |
| BP-002 | Vague Instructions | Primary failure cause. 40% of performance variance |
| BP-003 | Missing Output Format | Directly linked to hallucination reduction |

### P2: High Impact (Should Fix)

Consistent improvement when addressed.

| ID | Pattern | Research Basis |
|----|---------|----------------|
| BP-004 | Unstructured Prompt | "Structure > Length" confirmed |
| BP-005 | Missing Context | "More context = higher accuracy" confirmed |
| BP-006 | Complex Task Without Decomposition | ICLR 2023: 28% error reduction with decomposition |

### P3: Enhancement (Could Fix)

Incremental improvements in specific contexts.

| ID | Pattern | Research Basis |
|----|---------|----------------|
| BP-007 | Biased Examples | 40% of few-shot effectiveness depends on exemplar selection |
| BP-008 | No Uncertainty Permission | Allowing "I don't know" reduces hallucination |

## 3-Step Optimization Flow

### Step 1: Initial Analysis

**Input**: Target prompt
**Process**: Detect patterns (BP-001 through BP-008)
**Output**: `.claude/.rashomon/step1-analysis.md`

Contents:
- Detected issues by severity
- Location in prompt
- Original prompt preserved

### Step 2: Optimization

**Input**: Step 1 analysis
**Process**:
- Evaluate precision contribution
- Consolidate redundant improvements
- Apply in priority order (P1 > P2 > P3)
**Output**: `.claude/.rashomon/step2-optimized.md`

Contents:
- Before/after for each change
- Rationale
- Optimized prompt

### Step 3: Balance Adjustment

**Input**: Step 2 output
**Process**:
- Reference `references/execution-quality.yaml`
- Confirm all critical aspects are preserved
- Confirm constraints are proportionate
**Output**: Final optimized prompt

**CRITICAL**: Clean up temporary files after completion.

## Conditional Application

### BP-004 (Unstructured)

Apply 4-block pattern IF:
- Prompt longer than 3 sentences
- Contains multiple distinct instructions
- Has implicit section boundaries

Skip when:
- Single simple instruction
- Already clearly structured
- Structure would add unnecessary verbosity

### BP-006 (Decomposition)

Decompose IF:
- 3+ distinct objectives
- Sequential dependencies
- Each step can be quality-checked

**Key Insight**: Goal is EVALUABLE GRANULARITY with QUALITY CHECKPOINTS, not decomposition itself.

## Improvement Classification

| Classification | Definition | Interpretation |
|---------------|------------|----------------|
| **Structural** | Prompt structure, clarity, specificity improvements | Prompt writing technique |
| **Context Addition** | Project-specific information added from codebase investigation | Information advantage |
| **Expressive** | Different phrasing, equivalent substance | Neutral |
| **Variance** | Within LLM probabilistic variance | Original prompt sufficient |

**Principle**: Distinguish between prompt writing improvements (Structural) and information additions (Context Addition).

Reference: `references/execution-quality.yaml` for detailed criteria.

## References

- `references/patterns.yaml` - Detailed pattern definitions
- `references/execution-quality.yaml` - Quality evaluation criteria
