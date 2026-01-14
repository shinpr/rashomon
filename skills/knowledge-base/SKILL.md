---
name: knowledge-base
description: Project-specific prompt optimization knowledge management. Use when storing or retrieving learned patterns from comparisons. Provides schema, extraction criteria, capacity management, and retention scoring.
---

# Knowledge Base Skill

## Storage Location

```
{project_root}/.claude/.rashomon/prompt-knowledge.yaml
```

## Schema

```yaml
patterns:
  - name: "Pattern name"
    what_to_look_for: |
      When this pattern applies
    improvement: |
      How to improve when detected
    learned_from: "Date and context"
    confidence: 0.0-1.0
    times_applied: 0

anti_patterns:
  - name: "Anti-pattern name"
    what_to_look_for: |
      What to avoid
    why_bad: |
      Why problematic in this project
    learned_from: "Date and context"
    confidence: 0.0-1.0

metadata:
  last_updated: "ISO-8601 timestamp"
  total_comparisons: 0
  patterns_count: 0
  anti_patterns_count: 0
  max_entries: 20
```

## Extraction Criteria

### Save as Improvement Pattern

**ALL conditions must be true**:
- Optimized prompt showed **structural improvement** (not variance)
- Improvement is **project-specific** (not explained by BP-001~008)
- Pattern is likely to **recur** in this project

**Confidence Assignment**:
| Evidence | Confidence |
|----------|------------|
| Multiple comparisons confirmed | 0.8+ |
| Single comparison, clear effect | 0.5-0.7 |
| Effect present but uncertain | 0.3-0.5 |

**Minimum threshold**: 0.3 (entries below this are skipped)

### Save as Anti-Pattern

**ALL conditions must be true**:
- Original had problem **specific to this project**
- Problem is **project-specific** (beyond standard patterns BP-001~008)
- Problem **likely to recur**

### Extraction Scope

Save only entries that are:
- Project-specific (beyond standard best practices BP-001~008)
- Likely to recur in this project
- Showing clear effect (structural improvement, confidence ≥ 0.3)

## Capacity Management

**Maximum**: 20 entries (patterns + anti_patterns combined)

**Retention Score**: `confidence * (1 + log(times_applied + 1))`

This formula:
- Prioritizes high-confidence entries
- Rewards frequently-used patterns
- Treats all entries equally regardless of age

**Key Principle**: Old entries are valuable. Retention depends on confidence and usage frequency.

**Eviction Process**:
1. Calculate retention scores for all entries
2. Calculate score for new candidate
3. If new > lowest existing: remove lowest, add new
4. Otherwise: skip new entry

## Operations

### Retrieval

At start of prompt analysis:
1. Read `.claude/.rashomon/prompt-knowledge.yaml` (if exists)
2. For each entry, check `what_to_look_for` against current prompt
3. Return relevant entries with relevance scores
4. Increment `times_applied` for patterns used

### Storage

After comparison (if structural improvement found):
1. Evaluate against extraction criteria
2. Generate candidate entries
3. Check for duplicates
4. Apply capacity management
5. Write updated knowledge base
6. Update metadata

## Example Entry

```yaml
patterns:
  - name: "TypeScript interface reference"
    what_to_look_for: |
      Code generation prompts creating TypeScript types without
      referencing existing type definitions in src/types/
    improvement: |
      Add: "Reference existing types in src/types/ to maintain
      consistency and avoid duplicate type definitions"
    learned_from: "2026-01-14: Comparison showed better type reuse"
    confidence: 0.7
    times_applied: 3
```

## Feedback-Based Adjustments

When comparison results require knowledge base updates:

**Confidence Adjustments**:
- User confirms improvement: +0.1 (cap at 0.95)
- Pattern led to worse result: -0.2
- Remove entry if confidence < 0.2 after decrease

**Entry Management**:
- Add new entries from user insight (initial confidence: 0.5)
- Remove entries that fall below confidence threshold
