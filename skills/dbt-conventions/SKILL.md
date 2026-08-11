---
name: dbt-conventions
description: Repo-measured conventions for the cal-itp dbt project. Load when creating, renaming, or reviewing dbt models under warehouse/, when adding or reviewing dbt tests, or when interpreting what a green CI run or a clean dbt parse actually proves. Covers staging materialization, layer filename prefixes, description and primary-key-test guidelines, which paths have data tests enabled at all, and what can and cannot be verified without BigQuery credentials.
---

# cal-itp dbt conventions

Every rule below cites its in-repo source. Verify against the source before applying it.

## Layering

`warehouse/dbt_project.yml:47-48` sets `+materialized: view` for the `staging` layer.

That is the only layer-wide materialization default stated here. `intermediate` and `mart`
set materialization only on specific subfolders, so do not assume a default for them —
read `warehouse/dbt_project.yml` for the folder you are touching.

## Naming

Prefixes measured from `.sql` filenames under `warehouse/models/`:

| Layer | Total `.sql` | Prefixes in use |
|---|---|---|
| `staging` | 200 | `stg_` 186, `base_` 10, `int_` 4 |
| `intermediate` | 167 | `int_` 167 |
| `mart` | 252 | `fct_` 131, `dim_` 88, `bridge_` 19, other 14 |

The 14 `mart` files outside `fct_`/`dim_`/`bridge_` are `v2_` 6, `payments_` 4, `elavon_` 2,
`tides_` 1, `idx_` 1. Follow the dominant prefix for the layer unless an existing sibling
model in the same folder establishes another pattern. Some folders are tighter than the
layer: `staging/gtfs/` uses `stg_gtfs_schedule__<entity>`, so match the siblings you find
rather than stopping at the layer prefix.

`warehouse/dbt_project.yml` has no `staging_prefixes` key. The filenames on disk are the
only authority. These counts were measured 2026-08-11 and drift every time a model lands,
so recount instead of quoting them if anything looks off:

    find warehouse/models/<layer> -name '*.sql' -exec basename {} .sql \; \
      | sed 's/_.*//' | sort | uniq -c | sort -rn

## Guidelines

From `docs/warehouse/developing_dbt_models.md`, section `### Add dbt tests and documentation`:

- Sub-section `#### Documentation` (line 374): "All models should have a description and
  most columns should too."
- Sub-section `#### dbt tests` (line 364): "Most tables, especially in mart datasets,
  **should** have at least a primary key test that tests that there is a unique, non-null
  column."

Both are stated as `should`. They are guidance, not a gate — preserve that force when
citing them in review.

## Test enablement

`warehouse/dbt_project.yml:261-274` disables data tests for the whole project and re-enables
them for exactly four paths: `staging/payments`, `intermediate/payments`, `mart/payments`
and `mart/tides`.

A test added anywhere else parses cleanly, shows up in the YAML, and never executes. As of
2026-08-11 the project carries 220 enabled tests against 1029 disabled ones. This matters
most in the case the guidelines invite: adding a primary key test to a new mart model. Outside
those four paths it is inert.

Check before telling anyone a test does something:

    dbt ls -q -s <model> --resource-type test

Seven lines come back for a model under `mart/payments`; zero come back for one under
`mart/ntd_ridership`. Zero means disabled, not missing. Report that rather than reporting
that tests were added.

## Verification

On a local checkout without credentials, `dbt parse` is the check available to you. It
confirms the project compiles: SQL parses, `ref()`/`source()` resolve, YAML is valid.

`dbt run` and `dbt test` need a BigQuery connection — `warehouse/profiles.yml` targets
`type: bigquery` with `method: oauth`.

CI is not credential-free, and assuming it is will mislead you. `.github/workflows/deploy-dbt.yml`
authenticates through Workload Identity Federation and runs `dbt compile` and
`dbt run --full-refresh` against `cal-itp-data-infra-staging` on pull requests. No workflow runs
`dbt parse`, and no workflow runs `dbt test` at all — `docs/warehouse/developing_dbt_models.md:362`
says tests run daily in Airflow, which is after merge. `.github/pull_request_template.md` asks
the author to paste `dbt run` and `dbt test` output by hand, which is the tell that pre-merge
testing is a manual step rather than an automated gate. So a green PR means the model built
against real BigQuery. It does not mean a single test ran.

Two further limits on what a green PR build shows: in `warehouse/dbt_project.yml` the
`GTFS_SCHEDULE_START`, `GTFS_RT_START` and `TIDES_PRODUCT_START` vars fall back to roughly the
last seven days whenever the target is not `prod`, so a staging build covers a short window
rather than history, and it writes to the staging project, not prod.

A clean `dbt parse` says the model is well-formed. It says nothing about the data.
Never claim that a model produces correct results.
