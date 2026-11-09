# Final experiment evidence bundle

Created 2026-10-28T10:59:23+00:00. 232 attempts, 224 selected, 218 official reports. Analyze with the offline evaluator:

```bash
python -m tools.offline_eval analyze --manifest <this folder>/evidence/manifest.json --output <new folder>
```

The canonical patch artifact is submission.diff in corrected bundles; runner_patch.diff preserves the runner output. Selected runs with no_official_submission count as unresolved in the main results and have no official report. Supplementary records are separate and must not be merged into main results. See provenance/final_eval_index.json for patch sources and evaluation history. Official success comes only from Harness report.json files. Selected runs with an empty patch have `official_status: empty_patch_not_evaluated` (the Harness skips them; SWE-bench counts them as unresolved). labels.json is evaluation-only and must never be given to an agent. Cost completeness is recorded in provenance/cost_audit.json and each manifest record. When complete=false, cost_usd is null (unknown); recorded_cost_usd is only a partial subtotal. Raw run_result.json files are preserved and must not override these audit flags. All attempts, including excluded attempts with model calls, remain in the cost audit. Verify integrity with SHA256SUMS before analysis.


## Local slim checkout and complete archive

The text above is the original `final-evidence/README.md`, copied verbatim. This appended section describes packaging only. Original evidence JSON, patches, reports, labels, provenance and attempt selection are unchanged. The development evidence is in [../dev/](../dev/); it covers eight development tasks and makes no held-out or stability claim.

This formal bundle contains **232 attempts**, **224 selected runs**, and **218 selected official Harness reports**. The main comparison is 40 held-out tasks × four conditions at repeat 1 (160 selected runs); stability contributes 8 of those same tasks × four conditions × repeats 2–3 (64 additional selected runs). These are not 224 independent tasks. The eight excluded attempts remain in the manifest, small run records and cost audit.

### Main-result rule and the B=22 / B=23 discrepancy

Under the original rule above, selected runs with `no_official_submission` count as unresolved, and supplementary evaluations are excluded. The 40-task first-run resolved counts are **A=20/40, B=22/40, C=25/40, D=21/40**. There are six selected `no_official_submission` runs overall (five main runs and one extra stability run); no official report has been invented for them.

For `sympy__sympy-13757_B_ef22049a`, the unchanged main manifest has `official_status: no_official_submission`, `official_resolved: false`, and an empty official submission. The separately re-extracted patch was evaluated in `supp-partial-r1-B` and its supplementary report has `resolved: true` and `included_in_main_result: false` in the evaluation history. Adding this one supplementary success to B would give **23/40 (57.5%)**, while the original main rule gives **22/40 (55.0%)**. These are different reporting scopes; the supplementary result must not silently replace the main run. The report owner will decide which scope to present. No report source or result data were edited for this packaging task.

The supplementary evidence is separately available here:

- [Supplementary Harness report](supplementary/sympy__sympy-13757_B_ef22049a/supp-partial/report.json).
- [Supplementary patch](supplementary/sympy__sympy-13757_B_ef22049a/supp-partial/patch.diff).
- [Supplementary extraction record](supplementary/supplementary_partial.json) and [source audit](provenance/supplementary_partial_source.json).
- [Evaluation history](provenance/final_eval_index.json), key `evaluations.sympy__sympy-13757_B_ef22049a`, including the separate supplementary scope.

The final report presents the supplementary-inclusive scope (B=23/40) and states the rule in §5.

### Files and checksum scopes

The slim checkout retains all 232 small attempt records where recorded: `official/report.json`, `submission.diff`, `run_result.json`, `timings.json`, and `prompt_candidates.json`; it also retains the unchanged manifest, labels, all provenance (including submitted prediction JSONL files), and small supplementary records in their own directory. Missing original artifacts are not synthesized. Full trajectories, complete per-run rankings, Harness output/logs, D feedback raw records, and remaining original artifacts are indexed in [ARCHIVE_INDEX.md](ARCHIVE_INDEX.md).

- `SHA256SUMS` is newly generated for **this slim `final/` directory**, excluding itself.
- `SOURCE_SHA256SUMS` is the original complete-bundle checksum list, copied byte-for-byte. Its **3,564 entries all passed** against a fresh extraction. It intentionally lists files omitted here; verify it against the full `final-evidence/` directory, not against this slim checkout.
- The ZIP preserves the complete original bundle in `final-evidence/` (including its original README and SHA256SUMS). A separate `experiment-inputs/` directory adds the original three ranking JSON files, `task_ids.txt`, `stability_ids.txt`, `run_plan.jsonl`, and an input checksum list.

| Complete archive | Value |
|---|---|
| Filename | `role5-final-evidence-20261028.zip` |
| Compressed bytes | 18866074 |
| SHA-256 | `f32a071e29017b756ca0218307d439a2e2f5ce6d166303b56452163c27a5a74c` |
| Availability | Published as a [GitHub Release](https://github.com/235559649/DSA4213_group_work/releases/tag/role5-evidence-20261028); [download the complete ZIP](https://github.com/235559649/DSA4213_group_work/releases/download/role5-evidence-20261028/role5-final-evidence-20261028.zip) |

All archive members (3,572) passed CRC and byte-hash verification after ZIP creation. The original 3,565 files are unchanged; SHA256SUMS itself is the one file outside its own 3,564-entry list. Download the exact ZIP from the [published Release](https://github.com/235559649/DSA4213_group_work/releases/tag/role5-evidence-20261028) using the [direct asset link](https://github.com/235559649/DSA4213_group_work/releases/download/role5-evidence-20261028/role5-final-evidence-20261028.zip), then verify the SHA-256 above before extraction.

### Verify and recover full evidence

From `evaluation/role5/dev/`, the existing standard-library verifier can check this slim directory:

```sh
python -m tools.offline_eval verify --root ../final --checksums ../final/SHA256SUMS
```

[Download the complete ZIP](https://github.com/235559649/DSA4213_group_work/releases/download/role5-evidence-20261028/role5-final-evidence-20261028.zip), check its SHA-256 against the value above, then extract into a fresh directory outside the repository:

```sh
python -c "import hashlib,pathlib; p=pathlib.Path('role5-final-evidence-20261028.zip'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
python -m zipfile -e role5-final-evidence-20261028.zip <new-external-directory>
```

From `evaluation/role5/dev/`, check the extracted original checksum list and analyze the full manifest:

```sh
python -m tools.offline_eval verify --root <new-external-directory>/final-evidence --checksums <new-external-directory>/final-evidence/SHA256SUMS
python -m tools.offline_eval analyze --manifest <new-external-directory>/final-evidence/evidence/manifest.json --output <new-output-directory>
```

The preserved development evaluator exposes missing Harness reports as unknown rather than automatically applying this formal bundle's `no_official_submission` policy. Its generic success rates must therefore not be substituted for the main-rule counts above. For audited costs, use `provenance/cost_audit.json` and the manifest's completeness flags; do not replace unknown costs with partial `run_result.json` subtotals. Analysis reads recorded files; it does not rerun models or the Harness.

The analysis command above was tried locally on the complete original bundle. It wrote results for 232 attempts and 224 selected runs, with zero missing selected combinations, but returned exit code 1 with **218 audit flags**. Of these, 216 are `patch_matches_official_patch`: this older tool compares canonical `submission.diff` bytes directly with historical Harness patch bytes. All 216 run IDs are covered by the unchanged [167-run modification-line check](provenance/small_fuzz_167.json) or [49-run reapplication check](provenance/large_fuzz_49.json), both of which record `all_equal: true`; this packaging task did not rerun those historical patch-application checks. The other two flags are `response_count_matches` on excluded attempts `sphinx-doc__sphinx-11445_A_ecb50325` (12 responses / 13 calls) and `sphinx-doc__sphinx-11445_D_fa2973b6` (4 responses / 5 calls), already marked incomplete in `cost_audit.json`. These flags were preserved and must not be described as a clean full-evaluator validation. The independent primary-count calculation below avoids these unrelated comparisons and applies the declared main-result scope explicitly.

To independently reconstruct the primary resolved counts using only this slim directory, run the following Python from `evaluation/role5/final/` (also works against the full archive root):

```python
import json
from pathlib import Path

root = Path('.')
manifest = json.loads((root / 'evidence/manifest.json').read_text(encoding='utf-8'))
for condition in 'ABCD':
    runs = [r for r in manifest['records'] if r['selected']
            and r['experiment_id'] == 'main40_r1' and r['condition'] == condition]
    assert len(runs) == 40
    resolved = 0
    for run in runs:
        if run['official_status'] in {'no_official_submission', 'empty_patch_not_evaluated'}:
            continue
        report = root / run['artifacts']['official_report']
        outcome = json.loads(report.read_text(encoding='utf-8'))[run['task_id']]['resolved']
        assert type(outcome) is bool
        resolved += outcome
    print(f'{condition}={resolved}/40')
```

Expected: `A=20/40`, `B=22/40`, `C=25/40`, `D=21/40`. No supplementary path is read by this calculation.

### Task selection and rankings

`task_ids.txt` contains the 40 held-out task IDs; `stability_ids.txt` lists the eight stability tasks separately. Both lists match [the seed-25 selection](../../../experiments/heldout_seed25/); `run_plan.jsonl` is the recorded experiment plan. The selection package's plan retains its historical `not_run` status and is a frozen design record, not the execution ledger. Formal execution status comes from this bundle's manifest and official reports.

Three original ranking JSON files would add 14,367,710 bytes. To keep the combined delivery below 20 MB while preserving the original data bytes, the repository stores them as lossless `.json.gz` files. The ZIP also contains the uncompressed originals. The table hashes refer to the **decompressed original bytes**; the compressed-file hashes are in `SHA256SUMS`.

| Stored file | Compressed bytes | Original bytes | Original SHA-256 |
|---|---:|---:|---|
| `rankings/bm25_results.json.gz` | 620317 | 5818319 | `f1e5174cdd99f9cdbe16353f383b3caf3cc54be447118bfbbe4b469de9c27089` |
| `rankings/condition_c_results.json.gz` | 730041 | 6032871 | `cd6441ce069e73be756c5733b7311f0288dfafb9a5c18a7cc48088d419bf54cd` |
| `rankings/structural_results.json.gz` | 96262 | 2516520 | `3611812786977e6a0d10486df9c42816132308cb10668e4212a3006a9f47789d` |

To unpack rankings into a new external directory, run this Python from `final/` (replace the destination):

```python
import gzip
from pathlib import Path

out = Path('<new-external-ranking-directory>')
out.mkdir(parents=True, exist_ok=False)
for source in sorted(Path('rankings').glob('*.json.gz')):
    (out / source.stem).write_bytes(gzip.decompress(source.read_bytes()))
```

The source task-selection script was run from a clean copy under Python 3.14.6 using only the standard library. It regenerated 40 task IDs, eight stability IDs, `tasks.csv`, and 224 planned runs; all four output files matched the frozen results byte-for-byte. From the repository root, rerun its own check with `python experiments/heldout_seed25/scripts/reproduce.py`.

### Sensitive-information search

A local scan of the complete original bundle found no `sk-` or `api_key` matches, no credential-shaped tokens, and no private keys. `OPENROUTER` hits are model-class names or cost-error text; `Authorization` hits are upstream Sphinx test-code strings. Email-pattern hits include code decorators, test addresses, SWE-bench's setup address, and public upstream author/translator emails embedded in trajectories. Historical upstream user paths are also present. This is **not a claim that all personal identifiers are absent**. The original evidence was preserved without redaction; the local review includes file/line hit lists for the owner's publication decision.
