# Historical validation of the preserved full delivery

Prepared on 2026-10-28. Environment: Windows, Python 3.11.15. No model/API calls, agent runs, containers, or official Harness executions were performed during packaging.

## Executed checks

- **35 tests passed**: 30 synthetic boundary tests plus 5 recorded-evidence regression tests. See [historical test log](full-preparation-tests.txt).
- Full CLI analysis: **76 attempts, 63 selected runs, 8 unique tasks, 0 missing planned selected combinations, 0 explicit audit failures**.
- Official success counts reproduced: original dev5 A/B/C/D = 3/4/3/3 out of 5; original dev3 = 2/0/1/1 out of 3; first D fix = 1/3; second fix ABCD = 0/1/1/0 out of 3; latest four tasks = 1/1/2/2 out of 4.
- Latest four-task usage reproduced: 259 response-bearing model calls, 3,900,811 total tokens, USD 0.77604795.
- Second-fix excluded paid attempt retained: all attempts 163 calls / USD 0.5144133; selected attempts 149 calls / USD 0.4778583.
- Latest D timing reproduced: runtime 433.161599 s; initial localization 147.667181 s; feedback total 69.081411 s. Six deliveries, five rank-update routes, four actual ordering changes.
- The synthetic one-task D-only CLI example completed with no explicit audit failures.
- **1037 copied evidence files** compared byte-for-byte with their local source artifacts: no mismatches. Original artifacts were not edited.
- Main report/documentation local links checked for existing destinations. Archived provenance/source documents are historical evidence and are outside this authored-document link check.
- Common API-token/private-key patterns scanned in the staged files: no matches. This is a bounded pattern check, not a general security certification.
- No HTML, ZIP/tar archives, benchmark parquet, reference dataset JSON, virtual environments, or repository/index caches included.

## Important limits

This run checks the staged evidence and parser consistency. It does not establish server-side completeness, repeatability of model behavior, or causal improvement. Unknown fields/checks remain unknown, not passes. The official evaluations themselves are historical records.

All 63 nonempty trajectory submissions differ from patch files at the raw byte level because of historical serialization. The explicitly normalized comparison passes; 23 supplied native official patch artifacts additionally pass exact byte comparison. The failed formatting attempt has a workspace patch but no nonempty final submission and is not treated as a submitted repair.

Historical source-view annotations were preserved, not recomputed against absent Git blobs. Root-cause narratives remain evidence-linked human analysis. New D timings must not be backfilled into old experiments or counted twice with nested event time.

The first local unit-test invocation encountered the desktop sandbox's temporary-directory permission issue. The successful run used a writable workspace temporary directory via TEMP/TMP; no permission escalation was needed. No Linux execution was performed.

## Rechecking

From the package root:

```bash
python -m tools.offline_eval verify --root . --checksums CHECKSUMS.sha256
python -m unittest discover -s tests -v
python -m tools.offline_eval analyze --manifest evidence/manifest.json --output local-output/recheck
```

The checksum list covers every delivered file except itself. The `.gitattributes` file preserves recorded bytes across Git checkouts. Generated local outputs are ignored and not part of the published checksum list.
