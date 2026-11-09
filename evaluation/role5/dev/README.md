# Role 5: slim offline evaluation delivery

This is the **slim GitHub checkout**: English evaluation tools, three Chinese preliminary reports, precomputed metrics, and small recorded evidence. Complete raw evidence is supplied separately. The preserved original full directory is unchanged.

The data cover **8 unique development tasks**, **5 batches**, **76 attempts**, and **63 selected runs**. Reused tasks and retries are not independent samples. No held-out or stability claim is made.

## Read and inspect without the archive

- [Three preliminary reports](reports/README.md), including D timing and cross-version limitations.
- [Published metrics](results/analysis.json), [all attempts](results/run_summary.csv), and [D timing](results/d_timing.csv).
- [Evidence index](evidence/INDEX.md): local official results, patches, configurations, delivered candidates, and timing files.
- [English tool documentation](tools/offline_eval/README.md).
- [Current validation](validation/VALIDATION.md) and [Chinese submission guide](SUBMISSION_GUIDE.md).

Python 3.10+; standard library only. From this folder:

```bash
python -m tools.offline_eval verify --root . --checksums CHECKSUMS.sha256
python -m unittest discover -s tests -p test_offline_eval.py -v
python -m tools.offline_eval analyze --manifest examples/minimal/manifest.json --output local-output/example
```

The example is synthetic. These commands do not recompute the real experiment metrics. Default discovery of all tests reports the five full-evidence tests as skipped unless OFFLINE_EVAL_MANIFEST is set.

## Full evidence and reproduction

See [FULL_EVIDENCE.md](docs/FULL_EVIDENCE.md) for the exact archive filename, SHA-256, extraction layout, full analysis command, and integration-test commands. The archive is prepared locally and **has not been uploaded**; no public download URL is implied.

The slim checkout omits five large file types: full official test output, full D event records, complete initial rankings, agent trajectories, and D initial-ranking snapshots. Every omitted file is listed in the [archive index](evidence/ARCHIVE_INDEX.md), with its exact path and hash.

`evidence/manifest.json` retains the complete experiment contract. `results/` contains the previously computed full-evidence results. Do not remove missing artifact entries, convert unknown values to zero, or use this slim manifest alone for a partial analysis presented as full reproduction. After extracting the archive separately, analyze **the manifest in the extracted archive**.

## Interpretation and integration

Official repair success is read from existing Harness reports, never inferred from local tests or agent submission. Feedback delivery and improved ranks do not prove a repair. Failure explanations and historical source-view annotations remain human/audited interpretation, not automatically generated causal findings. Evaluation-only file labels must never be given to an agent.

Keep this folder intact under a new repository path such as `evaluation/role5/`. Keep the ZIP outside the normal code tree; it may later be provided as a Release asset or a course-approved shared artifact. Before sharing the repository with a reviewer, make the archive accessible and update `download_url` in evidence/ARCHIVE.json plus the retrieval documentation. No Git commit or upload has been performed.

The `.gitattributes` file preserves recorded bytes across platforms. Repository ignore rules must not exclude the intentional small official logs. Preserve existing project licensing; historical third-party excerpts retain their original provenance.
