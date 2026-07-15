# Evaluation Protocol

Execute after Phase A produces user-approved skill content. Phase B treats the source skill as read-only and runs scripts/eval-executor.py through claude -p.

## Executor Output Contract

~~~json
{
  "result": "final task output text",
  "status": "success | partial | error",
  "exit_code": 0,
  "skill_discovered": true,
  "skill_invoked": true,
  "skill_used": true,
  "skill_usage_evidence": [{"method": "Skill | Read", "value": "skill-name or verified SKILL.md path"}],
  "namespaced_skill_discoveries": ["plugin-name:skill-name"],
  "namespaced_skill_invocations": ["plugin-name:skill-name"],
  "skill_environment": {"mode": "expected | absent", "expected_path": "absolute path or null", "required_path": "canonical .claude/skills path in expected mode", "expected_fingerprint": "sha256 or null", "actual_fingerprint_before": "sha256 or null", "actual_fingerprint_after": "sha256 or null", "competing_paths": [], "valid": true},
  "base_sha": "git commit used to create the worktree",
  "files_modified": ["path/to/file"],
  "tools_used": ["Read", "Bash"],
  "error": "only on error or partial"
}
~~~

skill_invoked means the Skill tool named the project skill by exact name. A namespaced plugin match is diagnostic evidence and invalidates the run rather than satisfying skill_used. skill_used is true only when the verified environment contains exactly the expected skill copy and either Skill named the target exactly or Read opened that exact expected SKILL.md. files_modified is derived from the git working-tree state before and after execution, so changes made through Bash or NotebookEdit are included.

## Required Phase A Handoff

| Field | Source | Use |
|---|---|---|
| Skill name | Skill frontmatter | --skill-name |
| Source skill directory | Phase A write | Worktree copy source |
| Old skill directory snapshot + fingerprint | Update mode only, captured before any write | Complete old-version setup |
| Approved source directory fingerprint | Phase A final state | New/with-skill verification |
| Base SHA | Resolve once at Phase B start | Every worktree and result |
| Held-out test requests | Verbatim skill-dependent user requests | Direct trigger and execution input |
| Trigger scenarios | Phase A dialog | Scope validation only |
| Plugin path | Location of this script | Executor path |

The evaluation gate is blocked unless at least two complete held-out skill-dependent requests are available. Preserve held-out wording; generated description-aligned queries are diagnostics, not evidence of real trigger behavior.

Compute source and snapshot fingerprints with:

~~~bash
python3 {plugin_path}/skills/recipe-eval-skill/scripts/eval-executor.py \
  --fingerprint-skill-dir "{skill_directory}"
~~~

For a side expected to use the skill, invoke the executor with both `--expected-skill-dir "{absolute installed directory}"` and `--expected-skill-fingerprint "{recorded source fingerprint}"`. For creation baseline, use `--expect-skill-absent`. The executor restricts Claude setting sources to project and local configuration, disables auto memory, and rejects namespaced plugin invocations so external same-name skills do not satisfy the check.

## State Sequence

Register these states before execution and complete them in order:

1. cleanup_and_trigger
2. trigger_diagnosis
3. paired_execution
4. blind_assessment
5. identity_reveal
6. cleanup
7. combined_report

Each state records pass, blocked, or inconclusive plus its evidence. A later state starts only when the prior transition below permits it.

## 1. Cleanup and Trigger Check

Run orphan cleanup, then select one held-out request whose scenario is inside the skill scope:

~~~bash
./scripts/worktree-cleanup.sh --orphans [repo_root]
~~~

Resolve one base SHA before creating any worktree. Create a fresh worktree at that exact SHA, remove every competing target-skill discovery path, install only the approved skill version under .claude/skills/{skill_name}/, and verify its directory fingerprint. Execute the held-out request verbatim. Retry the same request up to three times because discovery and use can vary. Recreate the worktree at the pinned SHA before each attempt.

Trigger passes when:

- status is success;
- skill_discovered is true; and
- skill_used is true.
- skill_environment.valid is true; and
- base_sha equals the pinned Phase B SHA.

A direct target-SKILL.md Read satisfies use even when skill_invoked is false. Discovery failure caused by an incorrect installation path does not consume an attempt.

Report the exact request, attempts, discovery, use, usage evidence, and status.

## 2. Trigger Diagnosis

Skip when the trigger gate passed. After three failed attempts, classify using observed evidence:

| Diagnosis | Evidence | Transition |
|---|---|---|
| Installation failure | Target absent from init discovery list | Repair worktree setup and rerun State 1 |
| Held-out request out of scope | Request does not require a documented skill rule | Select another user-provided held-out request and rerun State 1 |
| General-knowledge overlap | Skill adds no project/product/organization-specific decision rule | Stop with blocked; recommend content authoring |
| Description mismatch | Request needs a specific skill rule, skill is installed, but remains unused | Return needs_authoring_revision to Phase A |
| Namespaced plugin collision | namespaced_skill_invocations contains a plugin skill with the same short name | Treat the attempt as invalid, disable the collision, and rerun State 1 in a fresh worktree |
| Execution failure | CLI/task error prevents a trigger observation | Stop with diagnostics; no trigger conclusion |

Phase B performs no source writes. For needs_authoring_revision, return the evidence and held-out request to Phase A. Phase A may invoke skill-creator and skill-reviewer, present the proposed description to the user, and write it only after approval. Then restart Phase B from State 1. Once a failed held-out request is exposed to authoring, retire it from evaluation and select an untouched held-out request for the restarted Phase B. Ask for a new verbatim request if none remain.
Allow at most two approved description revisions; persistent failure is blocked.

## 3. Sequential Paired Execution

Target three valid trials, with a maximum of five total trial attempts. Every attempt uses fresh worktrees at the pinned base SHA. Execute the two sides sequentially; alternate order between trials to reduce order effects. Concurrent claude -p calls are outside this protocol because they can interfere with skill discovery.

### Environment Expectations

| Mode | Side A | Side B |
|---|---|---|
| Creation | baseline: remove target from every discovery path | with-skill: install approved skill |
| Update | old-version: install complete saved directory snapshot | new-version: install complete approved source directory |

Required use conditions:

| Mode | Side | skill_discovered | skill_used |
|---|---|---:|---:|
| Creation | baseline | false | false |
| Creation | with-skill | true | true |
| Update | old-version | true | true |
| Update | new-version | true | true |

For each trial:

1. Create and configure both worktrees.
2. Remove all competing target copies, copy the complete expected directory, and verify the copied directory against its Phase A fingerprint. Creation baseline verifies target absence instead.
3. Run the held-out request unchanged on each side, sequentially, passing the expected absolute skill path and fingerprint to eval-executor.
4. Retry a side in a fresh worktree up to three times when its required use condition is unmet.
5. Mark the pair valid only when both statuses are success, both base_sha values equal the pinned SHA, both skill environments are valid, neither side reports a namespaced plugin invocation, and both sides satisfy the use table.
6. Store the paired result text and metadata, then clean both worktrees.

Never substitute the “best available” result for a failed requirement. Keep failed attempts as diagnostics. Continue trial attempts until three valid pairs are collected or five total trials have been attempted. Proceed with reduced confidence when two valid pairs remain; fewer than two is inconclusive.

## 4. Blind Assessment

Invoke skill-eval-reporter with anonymized valid pairs only:

~~~text
Test task: {verbatim held-out request}
Eval mode: {creation|update}

Trial 1:
  Result A: {text}
  Result B: {text}
...
~~~

Pass no identity, prompt/skill content, change summary, tool metadata, or failed-attempt metadata. The reporter must finish its dimension judgments and lock its blind recommendation before reveal.

## 5. Identity Reveal

After the blind output is complete, send:

~~~text
Identity mapping:
  A = {baseline|old-version}
  B = {with-skill|new-version}

Full metadata for each valid trial:
  status, base_sha, skill_discovered, skill_invoked, skill_used,
  skill_usage_evidence, namespaced_skill_discoveries,
  namespaced_skill_invocations, skill_environment, files_modified, tools_used

Target skill content:
  {approved SKILL.md and relevant references}
~~~

The post-reveal analysis may associate consistent output differences with skill availability or version. It must label causal explanations as hypotheses unless an output difference maps to a specific skill rule and repeats across valid trials.

## 6. Cleanup

Track every created worktree, result directory, and old-skill snapshot directory. Clean each in a finalization step on success, failure, timeout, or blocked transitions.

## 7. Combined Report

Return:

~~~markdown
# Skill Evaluation Summary

## Phase A: Skill Quality
- Grade: {A|B|C}
- Key findings: {summary}

## Phase B: Trigger
- Request: {verbatim held-out request}
- Discovered: {yes|no|unknown}
- Used: {yes|no|unknown}
- Evidence: {Skill invocation or direct Read}
- Diagnosis: {pass|blocked reason}

## Phase B: Execution
- Valid pairs: {n} (target 3, maximum 5 trial attempts)
- Status: {complete|inconclusive}
- Blind assessment: {reporter result, only when complete}
- Observed association: {evidence-proportional statement}

## Recommendation
{ship|revise|reject|collect more evidence}
~~~

Recommendation rules:

- ship: grade A/B, trigger pass, at least two valid pairs, and repeatable non-regressing benefit.
- revise: authoring or trigger evidence identifies a concrete correctable issue.
- reject: grade C or the skill adds no project-specific execution value.
- collect more evidence: comparison is inconclusive or differences do not repeat.

An inconclusive comparison has no winner and makes no skill-effectiveness recommendation.
