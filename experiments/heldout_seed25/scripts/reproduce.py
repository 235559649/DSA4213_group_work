"""Recreate the frozen seed-25 selection from public metadata and exclusions.

The default invocation checks the committed outputs. No model or harness is run.
"""

import argparse
import csv
import hashlib
import io
import json
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
RESULTS = ROOT / "results"
METADATA_FIELDS = (
    "instance_id",
    "repo",
    "base_commit",
    "version",
    "created_at",
    "difficulty",
    "environment_setup_commit",
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_exclusions(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def extract_task_ids(value):
    """Read ID fields from development artifacts, without reading outcome values."""
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"task_id", "instance_id"} and isinstance(item, str):
                found.add(item)
            elif key in {"task_ids", "instance_ids"} and isinstance(item, list):
                found.update(entry for entry in item if isinstance(entry, str))
            elif isinstance(item, (dict, list)):
                found.update(extract_task_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(extract_task_ids(item))
    return found


def verify_original_sources(source_root, metadata, exclusions, provenance):
    """Optional audit of the original Parquet and development evidence files."""
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RuntimeError("Source audit requires pyarrow") from exc

    dataset = source_root / provenance["dataset_path"]
    if sha256(dataset) != provenance["dataset_sha256"]:
        raise ValueError("Original Parquet checksum mismatch")
    rows = parquet.read_table(
        dataset, columns=list(METADATA_FIELDS)
    ).to_pylist()
    if sorted(rows, key=lambda row: row["instance_id"]) != metadata:
        raise ValueError("Committed metadata differs from original Parquet")

    found_ids = set()
    for source in provenance["exclusion_sources"]:
        path = source_root / source["path"]
        if sha256(path) != source["sha256"]:
            raise ValueError(f"Development evidence checksum mismatch: {path}")
        content = path.read_text(encoding="utf-8-sig")
        if source["format"] == "json":
            parsed = json.loads(content)
        elif source["format"] == "jsonl":
            parsed = [json.loads(line) for line in content.splitlines() if line.strip()]
        elif source["format"] == "csv":
            parsed = list(csv.DictReader(io.StringIO(content)))
        else:
            raise ValueError(f"Unknown source format: {source['format']}")
        extracted = extract_task_ids(parsed)
        if extracted != set(source["task_ids"]):
            raise ValueError(f"Development ID set changed: {path}")
        found_ids.update(extracted)
    if found_ids != {row["instance_id"] for row in exclusions}:
        raise ValueError("Development exclusion union changed")


def make_selection(config, metadata, exclusions, provenance):
    ids = [row["instance_id"] for row in metadata]
    if len(metadata) != provenance["counts"]["verified"] or len(ids) != len(set(ids)):
        raise ValueError("Verified metadata count or uniqueness changed")
    excluded_ids = {row["instance_id"] for row in exclusions}
    if len(excluded_ids) != provenance["counts"]["excluded"] or not excluded_ids <= set(ids):
        raise ValueError("Unexpected development exclusion set")

    eligible = [
        row for row in metadata
        if row["repo"] in config["repository_order"]
        and row["instance_id"] not in excluded_ids
    ]
    expected_pool = provenance["eligible_by_repo"]
    if (len(eligible) != provenance["counts"]["eligible"]
            or Counter(row["repo"] for row in eligible) != expected_pool):
        raise ValueError("Eligible pool differs from frozen sampling frame")

    seed = config["seed"]
    main_rng = random.Random(seed)
    stability_rng = random.Random(f"stability:{seed}")
    selected = []
    for repo in config["repository_order"]:
        candidates = sorted(
            (row for row in eligible if row["repo"] == repo),
            key=lambda row: row["instance_id"],
        )
        drawn = main_rng.sample(candidates, config["quotas"][repo])
        stability_ids = set(stability_rng.sample(
            sorted(row["instance_id"] for row in drawn),
            config["stability_per_repo"],
        ))
        for order, row in enumerate(drawn, 1):
            selected.append({
                **row,
                "seed": seed,
                "repo_draw_order": order,
                "in_stability_subset": row["instance_id"] in stability_ids,
                "planned_repeats_per_condition": (
                    config["total_repeats_for_stability"]
                    if row["instance_id"] in stability_ids else 1
                ),
            })
    if (len(selected) != sum(config["quotas"].values())
            or sum(row["in_stability_subset"] for row in selected)
            != config["stability_per_repo"] * len(config["repository_order"])):
        raise ValueError("Unexpected selected/stability counts")
    return selected


def make_run_plan(config, selected):
    runs = []
    for row in selected:
        for repeat in range(1, row["planned_repeats_per_condition"] + 1):
            for condition in config["conditions"]:
                runs.append({
                    "planned_run_key": (
                        f"seed{config['seed']}/{row['instance_id']}/{condition}/r{repeat}"
                    ),
                    "seed": config["seed"],
                    "instance_id": row["instance_id"],
                    "base_commit": row["base_commit"],
                    "condition": condition,
                    "repeat_id": repeat,
                    "role": "main" if repeat == 1 else "stability_additional",
                    "status": "not_run",
                })
    expected_runs = len(config["conditions"]) * (
        len(selected)
        + (config["total_repeats_for_stability"] - 1)
        * sum(row["in_stability_subset"] for row in selected)
    )
    if len(runs) != expected_runs:
        raise ValueError("Unexpected run-plan length")
    return runs


def check_committed(selected, runs):
    selected_ids = [row["instance_id"] for row in selected]
    stability_ids = [
        row["instance_id"] for row in selected if row["in_stability_subset"]
    ]
    if (RESULTS / "task_ids.txt").read_text(encoding="utf-8").splitlines() != selected_ids:
        raise ValueError("Task ID list differs from reproduced selection")
    if (RESULTS / "stability_ids.txt").read_text(encoding="utf-8").splitlines() != stability_ids:
        raise ValueError("Stability ID list differs from reproduced selection")
    with (RESULTS / "tasks.csv").open(encoding="utf-8-sig", newline="") as stream:
        committed_tasks = list(csv.DictReader(stream))
    if committed_tasks != [
        {key: str(value) for key, value in row.items()} for row in selected
    ]:
        raise ValueError("Task CSV differs from reproduced selection")
    committed_runs = [
        json.loads(line) for line in
        (RESULTS / "run_plan.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if committed_runs != runs:
        raise ValueError("Run plan differs from reproduced selection")


def write_outputs(output, selected, runs):
    output.mkdir(parents=True, exist_ok=False)
    with (output / "tasks.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)
    for name, ids in (
        ("task_ids.txt", [row["instance_id"] for row in selected]),
        ("stability_ids.txt", [
            row["instance_id"] for row in selected if row["in_stability_subset"]
        ]),
    ):
        (output / name).write_text("\n".join(ids) + "\n", encoding="utf-8")
    (output / "run_plan.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in runs),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Write a new copy to this absent directory")
    parser.add_argument(
        "--source-root", type=Path,
        help="Also audit the pinned Parquet and local development evidence files",
    )
    args = parser.parse_args()

    config = read_json(ROOT / "config.json")
    provenance = read_json(INPUTS / "source_provenance.json")
    for filename, expected in (
        ("benchmark_metadata.json", config["metadata_sha256"]),
        ("exclusions.csv", config["exclusions_sha256"]),
        ("source_provenance.json", config["source_provenance_sha256"]),
    ):
        if sha256(INPUTS / filename) != expected:
            raise ValueError(f"Input checksum mismatch: {filename}")
    metadata = read_json(INPUTS / "benchmark_metadata.json")
    exclusions = read_exclusions(INPUTS / "exclusions.csv")
    if args.source_root:
        verify_original_sources(args.source_root, metadata, exclusions, provenance)
    selected = make_selection(config, metadata, exclusions, provenance)
    runs = make_run_plan(config, selected)
    check_committed(selected, runs)
    if args.output_dir:
        write_outputs(args.output_dir, selected, runs)
    print("OK: 40 tasks; 8 stability tasks; 224 planned runs; committed selection reproduced")


if __name__ == "__main__":
    main()
