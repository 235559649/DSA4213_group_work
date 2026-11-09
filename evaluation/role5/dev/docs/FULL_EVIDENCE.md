# Complete evidence: retrieval and reproduction

## Archive identity

| Item | Value |
|---|---|
| Filename | `role5-full-evidence-20261028.zip` |
| ZIP SHA-256 | `2ef9db0992edefe0606c32987862956dabad4f7b7275b93294cc1b6d2face388` |
| Compressed bytes | 7966259 |
| Evidence files | 1044 |
| Files omitted from the slim checkout | 239 |
| Availability | Prepared locally; not uploaded |
| Public download URL | Not available yet |

The owner stores the ZIP in the separate `role5-evidence-archive-20261028` directory, alongside SHA256SUMS. Ask for that exact file when reviewing the project before publication. After a Release/shared-storage upload is authorized, the owner should add the real URL here and to [ARCHIVE.json](../evidence/ARCHIVE.json); no placeholder URL should be represented as live.

The ZIP contains all evidence, including the small files already in Git. It is not just the omitted-file delta, and it contains no model credentials or reference-repair dataset. Original source snapshots inside it are inert evidence, not installation instructions.

## Verify before extraction

Windows PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath ../role5-evidence-archive-20261028/role5-full-evidence-20261028.zip
```

Linux/macOS:

```bash
python -c "import hashlib,pathlib; p=pathlib.Path('../role5-evidence-archive-20261028/role5-full-evidence-20261028.zip'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

The result must exactly match the SHA-256 above. Stop on a mismatch. Adjust the archive's path if you downloaded it elsewhere.

## Extract into a separate directory

From the slim checkout, with the archive directory beside it:

```bash
python -m zipfile -e ../role5-evidence-archive-20261028/role5-full-evidence-20261028.zip ..
```

Use a fresh destination; do not overwrite an existing evidence extraction or the original full delivery. The resulting sibling folder is:

```text
role5-full-evidence-20261028/
  README.md
  FULL_EVIDENCE_CHECKSUMS.sha256
  evidence/
    manifest.json
    labels.json
    records/
    provenance/
    annotations/
```

The original evidence manifest has `package_root: ..`, so all its artifact paths resolve inside this extracted folder. No original local/server paths are used for loading evidence.

## Verify and recompute the complete results

Run the slim checkout's tool while pointing it at the **external archive manifest**:

```bash
python -m tools.offline_eval verify --root ../role5-full-evidence-20261028 --checksums ../role5-full-evidence-20261028/FULL_EVIDENCE_CHECKSUMS.sha256
python -m tools.offline_eval analyze --manifest ../role5-full-evidence-20261028/evidence/manifest.json --output local-output/full-recomputed
```

Expected: 1,044 evidence hashes pass; analysis reports 76 attempts, 63 selected runs, 0 missing selected combinations, and 0 explicit audit failures. Unknown checks remain unknown. The output directory must be new. The six generated files can be compared byte-for-byte with the published `results/` files.

This parses existing official reports and trajectories. It does not run an agent, call a model, execute archived code, or rerun the official Harness.

## Full-evidence integration tests

PowerShell:

```powershell
$env:OFFLINE_EVAL_MANIFEST = (Resolve-Path ../role5-full-evidence-20261028/evidence/manifest.json).Path
python -m unittest discover -s tests -p test_recorded_evidence.py -v
Remove-Item Env:OFFLINE_EVAL_MANIFEST
```

Linux/macOS:

```bash
OFFLINE_EVAL_MANIFEST=../role5-full-evidence-20261028/evidence/manifest.json python -m unittest discover -s tests -p test_recorded_evidence.py -v
```

There are five full-evidence integration tests. With no environment variable they skip explicitly; an explicitly configured missing/invalid manifest fails rather than silently skipping. The 30 synthetic boundary tests use no archived evidence.

## Following a report's archived link

Each archived link opens [ARCHIVE_INDEX.md](../evidence/ARCHIVE_INDEX.md) at a file ID. Its path is relative to the extracted root and its SHA-256 identifies the original file. Open that member locally to inspect the cited trajectory/message or ranking. Local links to small official reports and patches remain directly usable on GitHub.

## Two checksum scopes

- Root `CHECKSUMS.sha256`: the slim checkout only; no missing files are listed.
- Archive `FULL_EVIDENCE_CHECKSUMS.sha256`: every file under the extracted evidence directory.
- ZIP SHA-256 in [ARCHIVE.json](../evidence/ARCHIVE.json): the whole compressed archive, including its README and checksum list.

Old provenance manifests inside the evidence describe their historical exports; they are not the slim-checkout checksum list. Do not substitute those historical manifests for the appropriate current one.
