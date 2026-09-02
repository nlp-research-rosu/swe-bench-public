# verified500 full regression runbook

## Goal

Recheck official-resolved baseline/fvk patches with broader developer tests.
The main scope has 413 FVK-official-resolved instances:

- 405 instances where baseline and fvk both resolved: run both arms.
- 8 instances where only fvk resolved: run fvk only.
- 2 baseline-only resolved instances are archived as an optional add-on.

## Batch Model

The 413 instances are split into four recovery boundaries:

| batch | instances |
|---|---:|
| `regression001` | 104 |
| `regression002` | 103 |
| `regression003` | 103 |
| `regression004` | 103 |

A batch is not one giant concurrent job. It is a resumable queue. With
`--max-workers 1`, the runner processes one instance at a time:

```text
instance A: oracle -> baseline -> fvk
instance B: oracle -> baseline -> fvk
instance C: oracle -> fvk
...
```

With `--max-workers 2`, two instances run concurrently, but each instance still
runs its own contexts in order.

## Outputs

All full-regression artifacts stay under:

```text
verified500_regression/results/<run-id>/
```

Important files:

- `candidate_matrix.json`: copy of the candidate matrix used by the run.
- `run_manifest.json`: batch, selected instances, worker count, timeouts.
- `oracle/<instance>.json`: oracle context report.
- `contexts/<instance>/<arm>.json`: generated patch context report.
- `arms/<instance>/<arm>.json`: oracle-vs-generated comparison report.
- `logs/<instance>/<context>.log`: raw container output.
- `score_sheet.json`, `score_sheet.md`, `score_sheet.csv`: aggregate report.

Existing reports are reused. Re-running the same command resumes from the files
already present. Use `--force` only when intentionally replacing reports.

## Batch 1 Command

Use an x86_64 Linux Docker host for the real run.

First create the run directory and copy the matrix:

```bash
.venv/bin/python -m fvk_bench regression-full plan \
  --run-id verified500-regression-v1
```

Run batch 1 sequentially:

```bash
.venv/bin/python -m fvk_bench regression-full run \
  --run-id verified500-regression-v1 \
  --batch regression001 \
  --max-workers 1
```

Generate the score sheet after the batch finishes or after an interrupted run:

```bash
.venv/bin/python -m fvk_bench regression-full report \
  --run-id verified500-regression-v1
```

## One-Instance Smoke

Before launching all of `regression001`, run one known cached instance:

```bash
.venv/bin/python -m fvk_bench regression-full run \
  --run-id verified500-regression-smoke \
  --batch regression001 \
  --instances astropy__astropy-12907 \
  --max-workers 1 \
  --max-directives 1 \
  --skip-install

.venv/bin/python -m fvk_bench regression-full report \
  --run-id verified500-regression-smoke
```

This exercises the real `regression-full` runner without running Astropy's full
suite or reinstalling the project. It is a runner smoke, not a correctness
result. The real batch run must omit `--max-directives` and `--skip-install`.

## Status Meanings

Arm comparison reports use these main statuses:

- `clean`: no test passed by oracle failed under the generated arm.
- `regression_fail`: at least one oracle-passing test failed under the arm.
- `patch_apply_error`: generated patch did not apply.
- `test_patch_apply_error`: SWE-bench test patch did not apply.
- `infra_error`: container run did not produce usable directive metadata.
- `oracle_*`: oracle context failed before a usable comparison.

Only `regression_fail` is a confirmed full-regression failure. Infra and oracle
statuses are inconclusive and must not be counted as generated patch bugs.
Missing local SWE-bench eval images are recorded as `infra_error`; prepare or
pull the missing images, then re-run the same command to resume.

## Worker Guidance

Start with `--max-workers 1`. Full developer tests are much heavier than the
official FAIL_TO_PASS/PASS_TO_PASS tests, and Docker image pulls/builds can
dominate early runtime.

After one batch is stable, `--max-workers 2` is reasonable on a large x86_64
host. Keep the same worker count for runs you plan to compare directly.

## If Interrupted

Run the same command again:

```bash
.venv/bin/python -m fvk_bench regression-full run \
  --run-id verified500-regression-v1 \
  --batch regression001 \
  --max-workers 1
```

The runner skips existing `oracle/`, `contexts/`, and `arms/` reports unless
`--force` is passed.
