# Formal-Methods Review of SWE-bench Verified

This repository contains the results and reproduction materials for an
experiment over all 500 SWE-bench Verified instances. We asked whether general
formal-methods knowledge helps an LLM find problems in code that already passes
the benchmark's official tests.

## TL;DR

- The baseline resolved **407/500** instances; the FVK review resolved
  **413/500**.
- Both versions passed on 405 instances. FVK produced a different patch for
  [86 of those programs](verified500_analysis/REPORT.md).
- Case-by-case review found a substantive correctness, completeness, boundary,
  or robustness improvement in [60 of the 86 rewrites](verified500_fvk_baseline_buggy/README.md).
- In five cases, the FVK patch was judged more correct than the merged human
  fix.
- Three of the findings have
  [executable regression tests](verified500_analysis/ENHANCED_TESTS.md) that
  fail on the baseline and pass on FVK.

## Experiment

For each instance:

1. Codex solved the public issue normally, producing the baseline patch.
2. We resumed that frozen session, supplied the Formal Verification Kit's
   general guidance on formal methods, semantics, and verification, and asked
   the model to review its patch and rewrite it only if needed.
3. We evaluated both patches independently with the official SWE-bench harness.

The model was not given hidden test names or contents. The FVK arm used formal-
methods knowledge without calling a proof tool.

| Outcome | Count |
|---|---:|
| Baseline resolved | 407/500 |
| FVK resolved | 413/500 |
| Both resolved | 405/500 |
| Both resolved, different patch | 86 |
| Substantive FVK improvement after review | 60 |
| Excluded as equivalent, cosmetic, or insufficiently supported | 26 |

The 86 is a mechanical selection: both patches passed and their contents
differed. A changed patch is not automatically better. The 60 is the reviewed
subset where the evidence supports a real improvement that the official tests
did not distinguish.

## Read the analysis

- [Analysis of the 86 rewritten programs](verified500_analysis/REPORT.md)
- [The 60 substantive cases](verified500_fvk_baseline_buggy/README.md)
- [Three executable red/green regression tests](verified500_analysis/ENHANCED_TESTS.md)
- [Twenty-one deeper analyses and negative controls](verified500_analysis/README.md)
- [All 50 canonical runs and official scores](results/INDEX.md)
- [Machine-readable candidate matrix](results/candidate_matrix.json)

For a concrete example, start with
[`pydata__xarray-4094`](verified500_fvk_baseline_buggy/pydata__xarray-4094.md).

## Reproduce

Verify the published counts and severity breakdown directly from the checked-in
artifacts:

```bash
python scripts/verify_published_results.py
```

This verifies the accounting behind 407, 413, 405, 86, 60, and 26. The 60
qualitative judgments are supported individually by the linked case articles;
they are not an official SWE-bench metric.

To inspect or rerun the three added behavioral tests, follow
[`verified500_analysis/ENHANCED_TESTS.md`](verified500_analysis/ENHANCED_TESTS.md).
Rerunning them requires Docker and the standard SWE-bench evaluation images.

To run a new baseline/FVK experiment and evaluate it with the official harness,
see [`START.md`](START.md). Model generation is nondeterministic, so a new run
reproduces the method rather than necessarily producing byte-identical patches.
The saved artifacts are the source of truth for the published run.

## Scope and attribution

- “Resolved” means resolved by the official SWE-bench harness.
- The missed behaviors expose limits in the official test coverage; they do not
  redefine what counts as passing SWE-bench.
- Proof-shaped artifacts that were not machine-checked are described as
  proof-structured reasoning, not completed formal proofs.

This experiment repository is built on
[SWE-bench](https://github.com/SWE-bench/SWE-bench) and retains its MIT license.
See [`LICENSE`](LICENSE) for details. The Formal Verification Kit source is
available at
[`grosu/formal-verification-kit`](https://github.com/grosu/formal-verification-kit).
