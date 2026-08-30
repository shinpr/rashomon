---
name: knowledge-base
description: Retrieves and updates project-specific prompt knowledge from comparison evidence and user feedback. Use only for prompt analysis or post-comparison learning within a Rashomon evaluation.
user-invocable: false
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
    source: "comparison ID, report path, or user feedback"
    source_fingerprint: "stable hash or revision identifying the evidence"
    validity_scope: "project area, version range, or conditions where this applies"
    last_verified: "ISO-8601 timestamp"
    invalidated_when: "observable condition that requires revalidation"
    confidence: 0.0-1.0
    times_applied: 0

anti_patterns:
  - name: "Anti-pattern name"
    what_to_look_for: |
      What to avoid
    why_bad: |
      Why problematic in this project
    learned_from: "Date and context"
    source: "comparison ID, report path, or user feedback"
    source_fingerprint: "stable hash or revision identifying the evidence"
    validity_scope: "project area, version range, or conditions where this applies"
    last_verified: "ISO-8601 timestamp"
    invalidated_when: "observable condition that requires revalidation"
    confidence: 0.0-1.0
    times_applied: 0

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
- Improvement is **project-specific** (not explained by BP-001~009)
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
- Problem is **project-specific** (beyond standard patterns BP-001~009)
- Problem **likely to recur**

### Extraction Scope

Save only entries that are:
- Project-specific (beyond standard best practices BP-001~009)
- Likely to recur in this project
- Showing clear effect (structural improvement, confidence ≥ 0.3)

## Capacity Management

**Maximum**: 20 entries (patterns + anti_patterns combined)

**Retention Score**: `confidence * (1 + log(times_applied + 1))`

This formula:
- Prioritizes high-confidence entries
- Rewards frequently-used patterns
- Applies no direct age penalty; validity is evaluated separately

Age alone does not reduce retention. Before scoring, revalidate an entry when its `invalidated_when` condition is observed or its source fingerprint no longer matches. An entry with unresolved validity is excluded from retrieval until verified.

**Eviction Process**:
1. Calculate retention scores for all entries
2. Calculate score for new candidate
3. If new > lowest existing: remove lowest, add new
4. Otherwise: skip new entry

## Operations

### Retrieval

At start of prompt analysis:
1. Read `.claude/.rashomon/prompt-knowledge.yaml` (if exists)
2. Exclude entries whose validity condition is triggered or whose source fingerprint is stale
3. For each valid entry, check `what_to_look_for` against current prompt
4. Return relevant entries with relevance scores and provenance

Retrieval is read-only. It records proposed entry IDs in the prompt-analysis result; it does not increment counters or write the knowledge file.

### Storage

After a comparison and user feedback confirm how an entry affected execution:
1. Evaluate against extraction criteria
2. Generate candidate entries
3. Check for duplicates
4. Increment `times_applied` for each valid entry whose use is confirmed by the report
5. Revalidate source fingerprints and validity conditions
6. Apply capacity management
7. Write updated knowledge base
8. Update metadata

## Example Entry

```yaml
patterns:
  - name: "TypeScript interface reference"
    what_to_look_for: |
      Code generation prompts creating TypeScript types without referencing existing type definitions in src/types/
    improvement: |
      Add: "Reference existing types in src/types/ to maintain consistency and avoid duplicate type definitions"
    learned_from: "2026-01-14: Comparison showed better type reuse"
    source: "comparison: cmp-20260114-types"
    source_fingerprint: "git:abc123:src/types"
    validity_scope: "TypeScript generation under src/"
    last_verified: "2026-01-14T12:00:00Z"
    invalidated_when: "src/types is removed or its public type policy changes"
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
