# Role 5 evaluation evidence

This directory separates historical development evidence from the completed formal held-out experiment. Official Harness reports are the repair-success evidence; task reuse, infrastructure retries, and stability repeats are not additional independent tasks.

| Directory | Scope | Entry point |
|---|---|---|
| `dev/` | Eight development tasks, five batches, 76 attempts, 63 selected runs; no held-out or stability claim | [Development README](dev/README.md) |
| `final/` | 40 held-out tasks, eight-task stability subset, 232 attempts, 224 selected runs, 218 selected official reports | [Formal evidence and reproduction](final/README.md) |
| `../../experiments/heldout_seed25/` | Frozen seed-25 sampling inputs, exclusions, task metadata and reproduction script | [Selection README](../../experiments/heldout_seed25/README.md) |

The development slim package was copied byte-for-byte, including its independent checksum list and archive index. In `final/`, original data and reports are unchanged; the original README is preserved verbatim with packaging and reporting-scope notes appended. Three ranking JSON files are losslessly compressed as `.json.gz`; decompressing them recovers the exact original bytes. Full trajectories and other omitted raw files are listed by path, size and SHA-256 in [final/ARCHIVE_INDEX.md](final/ARCHIVE_INDEX.md).

From `dev/`, verify the two independent slim checksum lists:

```sh
python -m tools.offline_eval verify --root . --checksums CHECKSUMS.sha256
python -m tools.offline_eval verify --root ../final --checksums ../final/SHA256SUMS
```

From the repository root, reproduce the frozen task selection (standard library only):

```sh
python experiments/heldout_seed25/scripts/reproduce.py
```

Complete archives remain **outside Git**. The formal archive is published; the development archive remains local:

- Development: `role5-full-evidence-20261028.zip`, 7,966,259 bytes, SHA-256 `2ef9db0992edefe0606c32987862956dabad4f7b7275b93294cc1b6d2face388`. See [development retrieval instructions](dev/docs/FULL_EVIDENCE.md).
- Formal: `role5-final-evidence-20261028.zip`, 18,866,074 bytes, SHA-256 `f32a071e29017b756ca0218307d439a2e2f5ce6d166303b56452163c27a5a74c`. Available from the [GitHub Release](https://github.com/235559649/DSA4213_group_work/releases/tag/role5-evidence-20261028) or [direct ZIP download](https://github.com/235559649/DSA4213_group_work/releases/download/role5-evidence-20261028/role5-final-evidence-20261028.zip). See [formal retrieval instructions](final/README.md#verify-and-recover-full-evidence).

The formal archive is publicly available from the [Release](https://github.com/235559649/DSA4213_group_work/releases/tag/role5-evidence-20261028); only the development archive still requires obtaining the exact local file from the owner. The formal README explicitly documents the main-result B=22 and supplementary-inclusive B=23 scopes; the final report uses B=23/40 and states the rule in section 5.
