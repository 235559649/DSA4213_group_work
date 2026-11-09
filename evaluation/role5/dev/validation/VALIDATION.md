# Slim-delivery validation

Date: 2026-10-28. These checks apply to this new slim checkout and its separate complete-evidence ZIP. The [prior full-delivery validation](FULL_PREPARATION_20261028.md) is historical and remains separately identified.

## Executed checks

- **Original directory unchanged**: all 1,074 original file paths and SHA-256 values match the inventory captured before preparing the slim delivery. No original file was added, removed, or rewritten.
- **30 synthetic tests passed without archived evidence**. Default test discovery explicitly skipped the five evidence-dependent tests; skipped tests were not counted as passed. See [tests.txt](tests.txt).
- **5 full-evidence integration tests passed** after extracting the newly created ZIP into a separate temporary directory and setting OFFLINE_EVAL_MANIFEST. See [full-evidence-tests.txt](full-evidence-tests.txt).
- ZIP CRC verification passed. All **1,044 extracted evidence files** match the preserved source evidence byte-for-byte and pass FULL_EVIDENCE_CHECKSUMS.sha256.
- Complete analysis from the extracted archive reported **76 attempts, 63 selected runs, 8 unique tasks, 0 missing selected combinations, and 0 explicit audit failures**.
- All **six recomputed result files are byte-identical** to both the slim checkout's published results and the original full delivery's results.
- All **709 retained small run-evidence files** are byte-identical to their originals. The **239 omitted large files** exist in the independent archive with the documented hashes.
- The synthetic CLI example completed successfully without requiring external evidence.
- Authored report/documentation links resolve locally; every archived-file anchor points to an existing entry in ARCHIVE_INDEX.md. No unpublished URL is presented as a live download link.
- Tool code/documentation, tests, examples, and full-evidence reproduction instructions are in English. The three preliminary reports remain in Chinese.

## Checksum scopes

Root CHECKSUMS.sha256 covers every delivered slim file except itself. It does not include omitted raw files. The separate ZIP's hash is recorded in evidence/ARCHIVE.json, docs/FULL_EVIDENCE.md, and the external archive directory's SHA256SUMS. The extracted archive has its own FULL_EVIDENCE_CHECKSUMS.sha256 for all evidence files.

Only historical official outcomes were parsed. No agent, model API, container, archived source script, or official Harness was executed. This checks data preservation and reproducibility of the offline calculations, not model stability or causal effectiveness. Unknown original fields remain unknown. Historical source-view annotations were not reverified against absent Git blobs.

The tests ran on Windows with Python and a writable workspace temporary directory. No Linux execution or GitHub upload was performed. Raw evidence is intentionally extracted outside the slim checkout; temporary validation outputs are not part of the delivery.
