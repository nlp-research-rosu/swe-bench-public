# SWE-bench Verified Testing Status Summary

Current as of 2026-07-03.

This document summarizes the SWE-bench Verified testing data that has been run and can currently be reported from this repository. It covers both the official resolved results and the additional full-regression validation that has been completed so far.

The GitHub links below point to commit `24e88c582e21dfd2a3131ca6a105328d20045714`, which is the `main` commit that promoted the batch 1 and batch 2 regression results.

## High-Level Result

| Area | Current result |
|---|---|
| Official SWE-bench Verified scope | 500 unique instances |
| Official `baseline` resolved count | 407 / 500, 81.4% |
| Official `fvk` resolved count | 413 / 500, 82.6% |
| Official net difference | `fvk` resolves 6 more instances than `baseline` |
| Main full-regression scope | 413 `fvk`-resolved candidate instances, 818 generated arm runs |
| Full-regression completed so far | 207 / 413 candidate instances, 409 / 818 arm runs |
| Completed full-regression clean rate | 396 / 409 arm runs, 96.8% |
| Completed `baseline` regression clean rate | 196 / 202 arm runs, 97.0% |
| Completed `fvk` regression clean rate | 200 / 207 arm runs, 96.6% |
| Promoted infra/oracle infra failures | 0 in the completed score sheet |

The official resolved metric currently favors `fvk`: 413 resolved instances versus 407 for `baseline`. The broader regression validation is about halfway complete and has found a small number of regression failures in both arms. The completed regression results do not change the official resolved count; they report an additional quality check on the generated patches.

## Data Sources

Primary source files:

- [candidate_matrix.json][candidate-matrix]: official resolved matrix, regression candidates, and batch assignment.
- [BATCHES.md][batches-md]: human-readable batch breakdown.
- [regression001.json][batch-001], [regression002.json][batch-002], [regression003.json][batch-003], [regression004.json][batch-004]: machine-readable batch definitions.
- [score_sheet.csv][score-csv], [score_sheet.json][score-json], [score_sheet.md][score-md]: promoted full-regression score sheet for completed batches.
- [results README][results-readme]: description of tracked regression artifacts.

Detailed audit artifacts are stored in GitHub under:

- [arms reports][arms-tree]
- [generated contexts][contexts-tree]
- [run logs][logs-tree]
- [oracle reports][oracle-tree]

## What Was Tested

There are two reportable test layers.

| Layer | What it measures | Current status |
|---|---|---|
| Official SWE-bench Verified result | Whether each generated patch resolves the SWE-bench instance under the official fail-to-pass/pass-to-pass criteria. | Complete for the 500-instance matrix represented by the canonical verified500 runs. |
| Full-regression validation | Whether a generated patch regresses any test that passes under the gold-patch oracle context. | Completed for `regression001` and `regression002`; `regression003` and `regression004` are not yet represented in the promoted score sheet. |

The full-regression validation is stricter than the official resolved metric. It builds an oracle report from the gold patch, runs the generated `baseline` and/or `fvk` patch, and compares generated test outcomes against oracle-passing tests. An arm is marked `regression_fail` if an oracle-passing test becomes `FAILED`, `ERROR`, `SKIPPED`, missing, or otherwise non-passing in the generated run.

## Official SWE-bench Verified Results

These counts come from the canonical 50 verified500 runs summarized in [candidate_matrix.json][candidate-matrix].

| Metric | Count | Rate |
|---|---:|---:|
| Total unique SWE-bench Verified instances | 500 | 100.0% |
| `baseline` official resolved | 407 | 81.4% |
| `fvk` official resolved | 413 | 82.6% |
| Resolved by both `baseline` and `fvk` | 405 | 81.0% |
| `fvk`-only resolved | 8 | 1.6% |
| `baseline`-only resolved | 2 | 0.4% |
| Net `fvk` resolved gain over `baseline` | +6 | +1.2 pp |

The main full-regression scope is based on the 413 `fvk` official-resolved instances:

- 405 instances are resolved by both arms and have both `baseline` and `fvk` generated patches in the main regression scope.
- 8 instances are `fvk`-only and only run the `fvk` arm in the main regression scope.
- 2 `baseline`-only instances are stored separately in `baseline_only_addon.*` and are not part of the 413-instance main regression scope.

## Full-Regression Coverage

The main full-regression scope contains 413 candidate instances and 818 generated arm runs.

| Batch | Instances | Arm runs | Promoted score status | Repository coverage |
|---|---:|---:|---|---|
| `regression001` | 104 | 205 | Completed | `astropy`, `django` |
| `regression002` | 103 | 204 | Completed | `django` |
| `regression003` | 103 | 204 | Not in promoted score sheet | `django`, `matplotlib`, `pallets`, `psf`, `pydata`, `pylint-dev`, `pytest-dev`, `scikit-learn` |
| `regression004` | 103 | 205 | Not in promoted score sheet | `scikit-learn`, `sphinx-doc`, `sympy` |
| Total | 413 | 818 | 207 / 413 completed | 50.1% complete by candidate count |

Completed regression coverage:

- 207 / 413 regression candidates completed, 50.1%.
- 409 / 818 planned arm runs completed, 50.0%.
- 207 / 500 source SWE-bench Verified instances have completed full-regression validation, 41.4%.
- Completed instances cover all planned `astropy` instances and most planned `django` instances.

## Completed Full-Regression Results

Overall completed result:

| Arm | Evaluated arm runs | Clean | Regression fail | Clean rate |
|---|---:|---:|---:|---:|
| `baseline` | 202 | 196 | 6 | 97.0% |
| `fvk` | 207 | 200 | 7 | 96.6% |
| Combined | 409 | 396 | 13 | 96.8% |

Completed result by batch:

| Batch | Arm | Evaluated arm runs | Clean | Regression fail | Clean rate |
|---|---|---:|---:|---:|---:|
| `regression001` | `baseline` | 101 | 99 | 2 | 98.0% |
| `regression001` | `fvk` | 104 | 100 | 4 | 96.2% |
| `regression001` | Combined | 205 | 199 | 6 | 97.1% |
| `regression002` | `baseline` | 101 | 97 | 4 | 96.0% |
| `regression002` | `fvk` | 103 | 100 | 3 | 97.1% |
| `regression002` | Combined | 204 | 197 | 7 | 96.6% |

The `baseline` and `fvk` clean rates use separate denominators. The completed `fvk` denominator is larger because 5 completed `fvk`-only instances do not have a corresponding `baseline` arm in the main regression scope. All 5 completed `fvk`-only arms are regression-clean.

## Regression Failures Observed

The completed score sheet contains 13 regression-failing arm runs across 9 unique instances.

| Instance | Batch | Affected arm report(s) | Trigger count | Representative signal |
|---|---|---|---:|---|
| `astropy__astropy-12907` | `regression001` | [fvk][fail-astropy-12907-fvk] | 1 | `TestFlatLambdaCDM::test_toformat_model`: `PASSED` -> `FAILED` |
| `astropy__astropy-13579` | `regression001` | [fvk][fail-astropy-13579-fvk] | 1 | `TestFlatLambdaCDM::test_toformat_model`: `PASSED` -> `FAILED` |
| `django__django-11087` | `regression001` | [baseline][fail-django-11087-baseline] | 36 | Django admin delete/deleted-object tests: mostly `PASSED` -> `ERROR` |
| `django__django-12663` | `regression001` | [baseline][fail-django-12663-baseline], [fvk][fail-django-12663-fvk] | 2 | Filtered aggregate subquery annotation: `PASSED` -> `ERROR` |
| `django__django-13028` | `regression001` | [fvk][fail-django-13028-fvk] | 1 | Conditional window annotation: `PASSED` -> `FAILED` |
| `django__django-13925` | `regression002` | [baseline][fail-django-13925-baseline], [fvk][fail-django-13925-fvk] | 2 | PO file write-access test: `PASSED` -> `SKIPPED` |
| `django__django-13933` | `regression002` | [baseline][fail-django-13933-baseline], [fvk][fail-django-13933-fvk] | 16 | Model choice/admin widget/model formset tests: `PASSED` -> `FAILED` |
| `django__django-14170` | `regression002` | [baseline][fail-django-14170-baseline] | 1 | MySQL test database creation error test: `PASSED` -> `SKIPPED` |
| `django__django-15252` | `regression002` | [baseline][fail-django-15252-baseline], [fvk][fail-django-15252-fvk] | 2 | Migration `--fake-initial` test: `PASSED` -> `ERROR` |

Failure grouping:

| Group | Instances | Count |
|---|---|---:|
| `fvk`-specific regression failures | `astropy__astropy-12907`, `astropy__astropy-13579`, `django__django-13028` | 3 instances |
| `baseline`-specific regression failures | `django__django-11087`, `django__django-14170` | 2 instances |
| Shared `baseline` and `fvk` regression failures | `django__django-12663`, `django__django-13925`, `django__django-13933`, `django__django-15252` | 4 instances |

Two observed failures are `PASSED` -> `SKIPPED` transitions:

- `django__django-13925`, both arms.
- `django__django-14170`, `baseline` only.

The current score sheet treats these transitions as `regression_fail`.

## Infrastructure And Artifact Status

The promoted score sheet for `verified500-regression-v1` contains only `clean` and `regression_fail` statuses for completed batches. There are no promoted `infra` or `oracle_infra` failures remaining in the completed result set.

The completed runs include runner compatibility fixes that were required before the results were promoted:

- Python 3.6 compatibility for subprocess output handling.
- Python 3.5 compatibility for generated directive scripts.
- Docker image pull and per-instance image cleanup.
- Tracked result artifacts for `arms`, `contexts`, `logs`, and `oracle`.

The tracked result artifact tree for `verified500-regression-v1` is about 2.4 GB and contains 1,859 files.

## Current Readout

The official SWE-bench Verified result currently shows `fvk` ahead of `baseline` by 6 resolved instances on the 500-instance matrix.

The completed full-regression validation adds a stricter quality view over the generated patches. In the completed half of the regression scope, both arms are mostly clean: 97.0% clean for `baseline` and 96.6% clean for `fvk`. The observed regression failures are concentrated in 9 instances, with 3 `fvk`-specific, 2 `baseline`-specific, and 4 shared between both arms.

Because `regression003` and `regression004` are not yet in the promoted score sheet, the full-regression numbers should be read as the current completed-batch status rather than the final full-regression result.

[candidate-matrix]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/candidate_matrix.json
[batches-md]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/BATCHES.md
[batch-001]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/batches/regression001.json
[batch-002]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/batches/regression002.json
[batch-003]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/batches/regression003.json
[batch-004]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/batches/regression004.json
[score-csv]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/score_sheet.csv
[score-json]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/score_sheet.json
[score-md]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/score_sheet.md
[results-readme]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/README.md
[arms-tree]: https://github.com/nlp-research-rosu/swe-bench-public/tree/main/verified500_regression/results/verified500-regression-v1/arms
[contexts-tree]: https://github.com/nlp-research-rosu/swe-bench-public/tree/main/verified500_regression/results/verified500-regression-v1/contexts
[logs-tree]: https://github.com/nlp-research-rosu/swe-bench-public/tree/main/verified500_regression/results/verified500-regression-v1/logs
[oracle-tree]: https://github.com/nlp-research-rosu/swe-bench-public/tree/main/verified500_regression/results/verified500-regression-v1/oracle
[fail-astropy-12907-fvk]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/astropy__astropy-12907/fvk.json
[fail-astropy-13579-fvk]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/astropy__astropy-13579/fvk.json
[fail-django-11087-baseline]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-11087/baseline.json
[fail-django-12663-baseline]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-12663/baseline.json
[fail-django-12663-fvk]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-12663/fvk.json
[fail-django-13028-fvk]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-13028/fvk.json
[fail-django-13925-baseline]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-13925/baseline.json
[fail-django-13925-fvk]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-13925/fvk.json
[fail-django-13933-baseline]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-13933/baseline.json
[fail-django-13933-fvk]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-13933/fvk.json
[fail-django-14170-baseline]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-14170/baseline.json
[fail-django-15252-baseline]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-15252/baseline.json
[fail-django-15252-fvk]: https://github.com/nlp-research-rosu/swe-bench-public/blob/main/verified500_regression/results/verified500-regression-v1/arms/django__django-15252/fvk.json
