# Regression Result Artifacts

This directory keeps promoted regression run artifacts under version control.

Tracked per run:

- `run_manifest.json`
- `candidate_matrix.json`
- `score_sheet.csv`
- `score_sheet.json`
- `score_sheet.md`
- `arms/*/*.json`
- `contexts/*/*.json`
- `oracle/*.json`
- `logs/*/*.log`

Ignored per run:

- transient top-level rerun logs such as `batch*.log`
- local machine snapshots such as `docker_images_before.txt`

The tracked context, oracle, and log artifacts are large but preserve enough
detail to audit the promoted run without rerunning every instance.
