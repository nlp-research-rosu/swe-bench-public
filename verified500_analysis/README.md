# Supporting Verified500 analysis

The primary publication-facing analysis is
[the 60-case evidence set](../verified500_fvk_baseline_buggy/README.md).
This directory preserves deeper supporting material for 21 selected cases.

## What the numbers mean

Across the 500 canonical instances:

| Result | Count |
|---|---:|
| Baseline passed the official tests | 407 |
| FVK passed the official tests | 413 |
| Both passed | 405 |
| Both passed and produced identical patches | 319 |
| Both passed and produced different patches | 86 |
| Different-patch cases judged substantively better after FVK review | 60 |
| Different-patch cases excluded from that claim | 26 |

The 86 is a mechanical selection: both versions passed the benchmark and the
FVK patch differed from the baseline patch. It does not, by itself, say the
baseline was wrong. The 60 is the reviewed subset where the FVK change
addresses a real correctness, completeness, boundary, or robustness issue that
the official tests did not distinguish.

## Contents

- [REPORT.md](REPORT.md) explains the experiment and claim boundaries.
- [SUMMARY_TABLE.md](SUMMARY_TABLE.md) indexes the 21 detailed supporting
  analyses retained here.
- [ENHANCED_TESTS.md](ENHANCED_TESTS.md) records three added tests that are
  red on baseline and green on FVK.
- Each instance directory contains an `ANALYSIS.md` and source materials such
  as the baseline, FVK, and official human patches.

The canonical run selection and all per-instance official verdicts are in
[results/candidate_matrix.json](../results/candidate_matrix.json).
