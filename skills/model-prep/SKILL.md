---
name: model-prep
description: Prepares one new cal-itp dbt model for developer review. Reads the repo conventions, inspects sources and macros, drafts a colocated YAML entry and a minimal SQL model, lets the PreToolUse hook inspect the write, delegates a read-only documentation review, and runs dbt parse. Runs only by explicit request and never on its own initiative.
argument-hint: <new model request>
disable-model-invocation: true
---

# model-prep

`$ARGUMENTS` is the new model request. Treat it as the specification.

This skill supports **new `.sql` files under `warehouse/models/` only**. Anything
else is out of scope. The manual invocation is what authorizes the initial YAML
and SQL writes for this one model. It authorizes nothing else.

<constraints>
Do not bypass the PreToolUse hook. If it blocks the SQL write, stop. Do not
route around it with Bash, with a different tool, or by changing the file path.

Do not apply the subagent's proposal. It is a draft for a developer.

Every description and every test must rest on repository evidence. When evidence
is missing, write a TODO that names what is missing.
</constraints>

<workflow>

<phase name="1-conventions">
Read `${CLAUDE_PLUGIN_ROOT}/skills/dbt-conventions/SKILL.md` before anything
else. It carries the measured layer prefixes, the staging materialization and
the `should`-level guidelines. Recount prefixes from disk if its table looks
stale.
</phase>

<phase name="2-inspect">
Inspect the requested source models, the sibling SQL in the target directory and
the YAML files in that directory. Inspect each source's configuration and every
macro the sources call, since a macro can change what the grain means.

Report any access policy the requested grain cannot preserve. Look for row
access policies, `create_row_access_policy` usage and restricted source configs.
If the requested grain would aggregate across a policy boundary, say so before
drafting.
</phase>

<phase name="3-plan">
State four things before writing anything:

- the planned SQL path
- the planned YAML path
- the intended grain, as "one row per X", naming the SQL construct behind it
- the prefix evidence, meaning the counted prefixes for that layer and why the
  chosen prefix qualifies
</phase>

<phase name="4-gate">
Stop and report if any of these hold:

- the SQL target already exists
- the request names no source
- the request names no grain
- the request names no layer
- the request names no output columns

Do not guess a missing element. Ask the developer.
</phase>

<phase name="5-draft">
Draft a minimal model. Minimal means it produces the requested grain and the
requested columns, and nothing more. Draft the colocated YAML entry alongside
it. Reuse an upstream description only when a repository file supports it, and
cite that file.
</phase>

<phase name="6-write-yaml">
Write the YAML first. It must contain the exact model name and a description.
The hook's documentation rule reads the model's own directory, so the YAML must
exist and must carry `name: <stem>` before the SQL write is attempted.
</phase>

<phase name="7-write-sql">
Write the SQL with Write or Edit so the PreToolUse hook can inspect the call.
Never create the .sql file by another route.
</phase>

<phase name="8-hook">
If the hook blocks the write, stop. Report every reason it returned, verbatim.
Do not retry, do not rename the file and do not change its path. A blocked write
ends the run and goes back to the developer.
</phase>

<phase name="9-review">
Once both files exist, delegate a read-only review to the `backfill-docs`
subagent. Give it the model path and the YAML path.
</phase>

<phase name="10-macros">
Review every macro-dependent classification the subagent returns against the
macro implementation in `warehouse/macros/` or `warehouse/dbt_packages/`. A
label that depends on a macro is unchecked until you have read that macro.
</phase>

<phase name="11-hold">
Do not apply the subagent proposal. Keep it in the report for developer review.
</phase>

<phase name="12-parse">
Run `cd warehouse && dbt parse`. If parse fails, stop and report the error.
</phase>

</workflow>

<evidence_boundaries>
A successful write does not prove the hook ran. Report hook feedback only when
Claude Code actually returns it. If none came back, say that no hook feedback
was returned. Do not infer that the hook passed, and do not infer that it fired.

A clean `dbt parse` checks project structure and YAML syntax. It does not
execute the model, does not run any test and does not prove correct results.

You have not queried BigQuery. Do not claim a column contains particular values,
do not claim a test passes and do not claim the model is correct.
</evidence_boundaries>

<output_format>
Report in this order.

1. The SQL and YAML files created.
2. The intended grain and the repository evidence used.
3. Hook feedback, or the statement that no hook feedback was returned.
4. The `dbt parse` result.
5. The subagent's proposed changes, its exact test labels (REAL, TAUTOLOGY,
   UNVERIFIABLE) and your independent review of each one.
6. Decisions that still need a developer.
7. What remains unverified without BigQuery.

End with exactly this line:

Ready for developer review. No subagent proposal was applied automatically.
</output_format>
