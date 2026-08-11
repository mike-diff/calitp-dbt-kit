---
name: dbt-conventions
description: Repo-measured conventions for the cal-itp dbt project. Load when creating, renaming, or reviewing dbt models under warehouse/ — covers staging materialization, layer filename prefixes, description and primary-key-test guidelines, and what can be verified without BigQuery credentials.
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
| `mart` | 251 | `fct_` 130, `dim_` 88, `bridge_` 19, other 14 |

The 14 `mart` files outside `fct_`/`dim_`/`bridge_` are `v2_` 6, `payments_` 4, `elavon_` 2,
`tides_` 1, `idx_` 1. Follow the dominant prefix for the layer unless an existing sibling
model in the same folder establishes another pattern.

`warehouse/dbt_project.yml` has no `staging_prefixes` key. The filenames on disk are the
only authority for prefixes; recount them rather than trusting this table if it looks stale.

## Guidelines

From `docs/warehouse/developing_dbt_models.md`, section `### Add dbt tests and documentation`:

- Sub-section `#### Documentation` (line 374): "All models should have a description and
  most columns should too."
- Sub-section `#### dbt tests` (line 364): "Most tables, especially in mart datasets,
  **should** have at least a primary key test that tests that there is a unique, non-null
  column."

Both are stated as `should`. They are guidance, not a gate — preserve that force when
citing them in review.

## Verification

`dbt parse` is the only verification available without credentials. It checks that the
project compiles: SQL parses, `ref()`/`source()` resolve, YAML is valid.

`dbt run` and `dbt test` need a real BigQuery connection — `warehouse/profiles.yml` targets
`type: bigquery` with `method: oauth`. Without credentials they cannot run.

A clean `dbt parse` says the model is well-formed. It says nothing about the data.
Never claim that a model produces correct results.
