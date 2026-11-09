"""Manifest-driven analysis. No model, network, shell, or benchmark execution."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    """Resolve only package-relative paths, including on Windows."""
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or ":" in relative or "\\" in relative:
        raise ValueError(f"Expected a portable relative path: {relative}")
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes the package: {relative}")
    return path


def complete_sum(values: list[Any]) -> float | int | None:
    """An empty or partially unknown total is unknown, not zero."""
    return sum(values) if values and all(v is not None for v in values) else None


def measured(values: list[Any]) -> dict[str, Any]:
    known = [v for v in values if v is not None]
    return {"sum": sum(known) if known else None, "known": len(known), "total": len(values),
            "complete": len(known) == len(values) and bool(values)}


def response_usage(messages: list[dict], expected_calls: int | None) -> dict:
    """Count response-bearing messages, including formatting-error responses."""
    responses = [m.get("extra", {}).get("response") for m in messages]
    responses = [r for r in responses if isinstance(r, dict)]
    usage = [r.get("usage") or {} for r in responses]
    calls = len(responses) if responses or expected_calls == 0 else None
    fields = {"input_tokens": "prompt_tokens", "output_tokens": "completion_tokens",
              "total_tokens": "total_tokens", "cost_usd": "cost"}
    result = {key: complete_sum([u.get(source) for u in usage]) for key, source in fields.items()}
    result["cached_input_tokens"] = complete_sum([
        (u.get("prompt_tokens_details") or {}).get("cached_tokens") for u in usage])
    if expected_calls == 0 and not responses:
        result.update({key: 0 for key in result})
    result.update({"api_calls": calls, "recorded_api_calls": expected_calls,
                   "response_count_matches": calls == expected_calls if expected_calls is not None else None})
    if expected_calls is not None and calls != expected_calls:
        # Do not present partial response totals as complete run totals.
        result["partial_response_totals"] = {key: result[key] for key in fields}
        result.update({key: None for key in fields})
        result["cached_input_tokens"] = None
    return result


def ranking_rows(value: Any) -> list[dict] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("A ranking must be a list of file/rank records")
    seen_files, seen_ranks = set(), set()
    for row in value:
        file, rank = row.get("file"), row.get("rank")
        if not isinstance(file, str) or not file or type(rank) is not int or rank < 1:
            raise ValueError("Invalid file or rank in ranking record")
        if file in seen_files or rank in seen_ranks:
            raise ValueError("Duplicate file or rank in ranking record")
        seen_files.add(file)
        seen_ranks.add(rank)
    # Prompt lists can retain non-contiguous full-ranking ranks.
    return value


def localization(full: list[dict] | None, visible: list[dict] | None,
                 targets: list[str] | None, condition: str) -> dict:
    empty = {"rr": None, "hit1": None, "hit5": None, "hit20": None,
             "recall5": None, "visible_hit": None, "visible_recall": None,
             "target_ranks": None, "target_display_positions": None}
    if condition == "A" or not targets:
        return empty
    if full is not None:
        rank_map = {r["file"]: r["rank"] for r in ranking_rows(full)}
        ranks = {t: rank_map.get(t) for t in targets}
        found = [r for r in ranks.values() if r is not None]
        first = min(found) if found else None
        empty.update({"target_ranks": ranks, "rr": 1 / first if first else 0,
                      "hit1": int(bool(first and first <= 1)), "hit5": int(bool(first and first <= 5)),
                      "hit20": int(bool(first and first <= 20)),
                      "recall5": sum(r is not None and r <= 5 for r in ranks.values()) / len(targets)})
    if visible is not None:
        positions = {r["file"]: i for i, r in enumerate(ranking_rows(visible), 1)}
        target_positions = {t: positions.get(t) for t in targets}
        count = sum(p is not None for p in target_positions.values())
        empty.update({"visible_hit": int(count > 0), "visible_recall": count / len(targets),
                      "target_display_positions": target_positions})
    return empty


def official_result(report: dict | None, task: str) -> dict:
    result = {"resolved": None, "patch_applied": None, "official_infra_failure": None,
              "f2p_passed": None, "f2p_total": None, "p2p_passed": None, "p2p_total": None}
    if report is None:
        return result
    if task not in report or not isinstance(report[task], dict):
        raise ValueError(f"Official report does not contain task {task}")
    item = report[task]
    result.update({"resolved": item.get("resolved"), "patch_applied": item.get("patch_successfully_applied"),
                   "official_infra_failure": item.get("infra_failure")})
    for field in ("resolved", "patch_applied", "official_infra_failure"):
        if result[field] is not None and type(result[field]) is not bool:
            raise ValueError(f"Official {field} must be a Boolean or null")
    for name, prefix in (("FAIL_TO_PASS", "f2p"), ("PASS_TO_PASS", "p2p")):
        tests = item.get("tests_status", {}).get(name)
        if tests is not None:
            success, failure = tests.get("success"), tests.get("failure")
            if isinstance(success, list) and isinstance(failure, list):
                result[prefix + "_passed"] = len(success)
                result[prefix + "_total"] = len(success) + len(failure)
    return result


def feedback_events(events: list[dict], messages: list[dict], targets: list[str] | None) -> list[dict]:
    output = []
    last_delivery_index = -1
    for sequence, event in enumerate(events, 1):
        context = event.get("delivered_context")
        matches = [i for i, m in enumerate(messages) if i > last_delivery_index and isinstance(context, str) and context
                   and isinstance(m.get("content"), str) and context in m["content"]]
        digest = sha256(context.encode("utf-8")) if context else None
        expected = event.get("delivered_context_sha256")
        before, after = event.get("before_ranking"), event.get("proposed_ranking")
        order_changed = None
        if before is not None and after is not None:
            order_changed = [r["file"] for r in sorted(ranking_rows(before), key=lambda r: r["rank"])] != [
                r["file"] for r in sorted(ranking_rows(after), key=lambda r: r["rank"])]
        row = {"sequence": sequence, "event_id": event.get("event_id"), "step": event.get("step"),
               "returncode": event.get("returncode"), "usable": event.get("analysis", {}).get("usable"),
               "route": event.get("feedback_route"), "update_applied": event.get("update_applied"),
               "status": event.get("update_status"), "order_changed": order_changed,
               "delivery_found": bool(matches) if context else None,
               "delivery_message_indices": matches, "delivery_hash_matches": digest == expected if expected else None,
               "delivered_before_model_call_recorded": event.get("delivered_before_model_call"),
               "processing_seconds": event.get("feedback_processing_seconds"),
               "before_rr": localization(before, None, targets, "D")["rr"],
               "after_rr": localization(after, None, targets, "D")["rr"]}
        # Check delivery timing from the actual response-bearing trajectory, not just its claim.
        if matches:
            last_delivery_index = matches[0]
            actual_call = 1 + sum(bool(m.get("extra", {}).get("response")) for m in messages[:matches[0] + 1])
            row["next_model_call_from_trajectory"] = actual_call
            row["delivery_call_matches"] = actual_call == event.get("delivered_before_model_call") if event.get("delivered_before_model_call") is not None else None
        output.append(row)
    return output


def feedback_summary(events: list[dict], recorded: bool) -> dict:
    """Separate localization eligibility from diagnostic delivery."""
    first = next((event for event in events if event["usable"] is True), None)
    delivered = next((event for event in events if event["delivery_found"] is True), None)
    if not recorded:
        status = "not_recorded"
    elif not events:
        status = "no_recorded_failure_event"
    elif first is None:
        status = "no_usable_localization_event" if all(e["usable"] is False for e in events) else "usability_incomplete"
    elif first["update_applied"] is not True:
        status = "first_usable_not_applied"
    else:
        status = "first_usable_delivered" if first["delivery_found"] else "first_usable_delivery_unverified"
    delta = None
    if first and first["update_applied"] is True and first["before_rr"] is not None and first["after_rr"] is not None:
        delta = first["after_rr"] - first["before_rr"]
    return {"event_count": len(events) if recorded else None, "events": events, "status": status,
            "first_usable": first, "first_delivered": delivered, "first_usable_delta_rr": delta}


def load_manifest(path: Path) -> tuple[dict, Path]:
    manifest = read_json(path)
    if manifest.get("schema_version") != 1:
        raise ValueError("Only manifest schema_version=1 is supported")
    root = (path.parent / manifest.get("package_root", ".")).resolve()
    ids, selected_keys, experiment_ids = set(), set(), set()
    for experiment in manifest["experiments"]:
        if experiment["id"] in experiment_ids:
            raise ValueError("Duplicate experiment ID")
        experiment_ids.add(experiment["id"])
        for field in ("tasks", "conditions", "repeat_ids"):
            values = experiment[field]
            if not values or len(values) != len(set(values)):
                raise ValueError(f"Experiment {field} must be a nonempty list of unique values")
    plans = {e["id"]: e for e in manifest["experiments"]}
    for row in manifest["records"]:
        if row["experiment_id"] not in experiment_ids:
            raise ValueError("Unknown experiment ID")
        plan = plans[row["experiment_id"]]
        if row["task_id"] not in plan["tasks"] or row["condition"] not in plan["conditions"] or row["repeat_id"] not in plan["repeat_ids"]:
            raise ValueError("Attempt is outside the declared experiment plan")
        key = (row["experiment_id"], row["run_id"])
        if key in ids:
            raise ValueError("Duplicate run identity")
        ids.add(key)
        if type(row["selected"]) is not bool or not row.get("selection_reason"):
            raise ValueError("Explicit selected Boolean and selection_reason are required")
        if not row.get("repeat_id") or not row.get("attempt_id"):
            raise ValueError("Separate repeat_id and attempt_id are required")
        if row["selected"]:
            key = (row["experiment_id"], row["task_id"], row["condition"], row["repeat_id"])
            if key in selected_keys:
                raise ValueError("Multiple selected attempts for one task/condition/repeat")
            selected_keys.add(key)
        for relative in row["artifacts"].values():
            file = safe_path(root, relative)
            if not file.is_file():
                raise ValueError(f"Listed artifact is missing: {relative}")
    return manifest, root


def analyze_record(meta: dict, root: Path, labels: dict) -> dict:
    artifacts = meta["artifacts"]

    def artifact(kind: str, default: Any = None) -> Any:
        return read_json(safe_path(root, artifacts[kind])) if kind in artifacts else default

    native = artifact("result")
    for key in ("run_id", "task_id", "condition"):
        if native[key] != meta[key]:
            raise ValueError(f"Run identity mismatch for {key}: {meta['run_id']}")
    trajectory = artifact("trajectory", {})
    messages = trajectory.get("messages", [])
    expected = native.get("usage", {}).get("api_calls")
    usage = response_usage(messages, expected)
    timings = artifact("timings", {})
    config = native.get("config", {})
    feedback = config.get("failure_feedback", {})
    target = labels.get(meta["task_id"], {}).get("paths")
    events = []
    if "feedback_events" in artifacts:
        events = [json.loads(line) for line in safe_path(root, artifacts["feedback_events"]).read_text("utf-8-sig").splitlines() if line.strip()]
    event_rows = feedback_events(events, messages, target)
    prompt_hashes = {}
    for role in ("system", "user"):
        content = next((m.get("content") for m in messages if m.get("role") == role), None)
        prompt_hashes[role + "_sha256"] = sha256(content.encode("utf-8")) if isinstance(content, str) else None
    result = {k: meta[k] for k in ("experiment_id", "run_id", "task_id", "condition", "repeat_id", "attempt_id", "selected", "selection_reason")}
    result.update({"status": native.get("status"), "termination_reason": native.get("termination_reason"),
                   "model": native.get("model"), "base_commit": config.get("base_commit"),
                   "runtime_seconds": native.get("runtime_seconds"),
                   "agent_wall_seconds": timings.get("agent_wall_seconds"),
                   "harness_seconds": timings.get("harness_seconds"),
                   "initial_localization_seconds": feedback.get("initial_localization_seconds"),
                   "feedback_total_seconds": feedback.get("feedback_total_seconds"),
                   "legacy_localization_overhead_seconds": feedback.get("localization_overhead_seconds"),
                   "reported_cost_usd": native.get("usage", {}).get("cost_usd"), **usage, **prompt_hashes})
    result.update(official_result(artifact("official_report"), meta["task_id"]))
    result["localization"] = localization(artifact("ranking"), artifact("prompt_candidates"), target, meta["condition"])
    result["feedback"] = feedback_summary(event_rows, "feedback_events" in artifacts)
    initial = result["initial_localization_seconds"]
    feedback_time = result["feedback_total_seconds"]
    overhead = complete_sum([initial, feedback_time])
    runtime = result["runtime_seconds"]
    result["d_timing"] = {
        "initial_plus_feedback_seconds": overhead,
        "initial_plus_feedback_runtime_fraction": overhead / runtime if overhead is not None and runtime else None,
        "recorded_event_processing": measured([e["processing_seconds"] for e in event_rows]),
        "undelivered_event_processing": measured([
            e["processing_seconds"] for e in event_rows if e["delivery_found"] is not True]),
    } if meta["condition"] == "D" else None
    result["artifacts"] = artifacts
    result["checks"] = {"response_count_matches": usage["response_count_matches"]}
    cost, reported = usage["cost_usd"], result["reported_cost_usd"]
    result["checks"]["cost_matches"] = abs(cost - reported) < 1e-8 if cost is not None and reported is not None else None
    if "patch" in artifacts:
        patch = safe_path(root, artifacts["patch"]).read_bytes()
        result["patch_sha256"] = sha256(patch)
        submission = trajectory.get("info", {}).get("submission")
        # Writers serialize the submitted patch with LF and strip surrounding
        # whitespace. Preserve byte hashes and explicitly name this weaker check.
        result["patch_equals_submission_bytes"] = patch == submission.encode("utf-8") if submission else None
        result["checks"]["patch_matches_normalized_submission"] = (
            patch.decode("utf-8").replace("\r\n", "\n").strip() == submission.replace("\r\n", "\n").strip()
            if submission else None)
        if "official_patch" in artifacts:
            result["checks"]["patch_matches_official_patch"] = patch == safe_path(root, artifacts["official_patch"]).read_bytes()
    if "effective_task" in artifacts and messages:
        task_text = safe_path(root, artifacts["effective_task"]).read_bytes().decode("utf-8")
        user_text = next((m.get("content") for m in messages if m.get("role") == "user"), "")
        result["checks"]["effective_task_delivered"] = task_text in user_text
    if "prompt_candidates" in artifacts and messages and meta["condition"] != "A":
        user_text = next((m.get("content") for m in messages if m.get("role") == "user"), "")
        result["checks"]["prompt_candidate_paths_delivered"] = all(
            row["file"] in user_text for row in ranking_rows(artifact("prompt_candidates")))
    return result


COST_FIELDS = ("api_calls", "cost_usd", "total_tokens", "runtime_seconds", "agent_wall_seconds",
               "harness_seconds", "initial_localization_seconds", "feedback_total_seconds")


def summarize(rows: list[dict], expected: int | None = None) -> dict:
    chosen = [r for r in rows if r["selected"]]
    resolved = sum(r["resolved"] is True for r in chosen)
    evaluated = sum(r["resolved"] is not None for r in chosen)
    result = {"attempts": len(rows), "selected": len(chosen), "expected": expected,
              "missing_selected": max(0, expected - len(chosen)) if expected is not None else None,
              "official_evaluated": evaluated, "resolved": resolved,
              "resolved_rate_evaluated": resolved / evaluated if evaluated else None,
              "resolved_rate_selected": resolved / len(chosen) if chosen and evaluated == len(chosen) else None,
              "selected_costs": {field: measured([r.get(field) for r in chosen]) for field in COST_FIELDS},
              "all_attempt_costs": {field: measured([r.get(field) for r in rows]) for field in COST_FIELDS}}
    result["localization"] = {}
    for key in ("rr", "hit1", "hit5", "hit20", "recall5", "visible_hit", "visible_recall"):
        values = [r["localization"][key] for r in chosen if r["localization"][key] is not None]
        result["localization"][key] = {"mean": sum(values) / len(values) if values else None, "known": len(values), "selected": len(chosen)}
    return result


def paired_rows(rows: list[dict], left: list[str], right: list[str], conditions: tuple[str, str] | None = None) -> list[dict]:
    """Join on task/repeat (and condition for cross-version comparisons)."""
    def index(experiments: list[str], condition: str | None) -> dict:
        result = {}
        for row in rows:
            if not row["selected"] or row["experiment_id"] not in experiments:
                continue
            if condition is not None and row["condition"] != condition:
                continue
            key = (row["task_id"], row["repeat_id"], row["condition"] if condition is None else "paired")
            if key in result:
                raise ValueError(f"Ambiguous comparison: duplicate task/repeat/condition {key}")
            result[key] = row
        return result
    before = index(left, conditions[0] if conditions else None)
    after = index(right, conditions[1] if conditions else None)
    output = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        # Keep unmatched records visible; they must not silently enter paired rates.
        entry = {"task_id": key[0], "repeat_id": key[1], "condition": key[2],
                 "baseline_run_id": a["run_id"] if a else None,
                 "candidate_run_id": b["run_id"] if b else None, "matched": bool(a and b)}
        if a and b:
            entry.update({"baseline_resolved": a["resolved"], "candidate_resolved": b["resolved"],
                          "resolved_delta": int(b["resolved"]) - int(a["resolved"]) if a["resolved"] is not None and b["resolved"] is not None else None})
            for field in ("base_commit", "model", "system_sha256", "user_sha256"):
                entry[field + "_same"] = a[field] == b[field] if a[field] is not None and b[field] is not None else None
            for field in ("cost_usd", "runtime_seconds", "api_calls"):
                entry[field + "_delta"] = b[field] - a[field] if a[field] is not None and b[field] is not None else None
        output.append(entry)
    return output


def analyze(manifest_path: Path) -> dict:
    manifest, root = load_manifest(manifest_path)
    labels = read_json(safe_path(root, manifest["labels"])) if manifest.get("labels") else {}
    rows = [analyze_record(meta, root, labels) for meta in manifest["records"]]
    summaries = []
    missing = []
    for exp in manifest["experiments"]:
        declared = {(t, c, r) for t in exp["tasks"] for c in exp["conditions"] for r in exp["repeat_ids"]}
        actual = {(r["task_id"], r["condition"], r["repeat_id"]) for r in rows if r["experiment_id"] == exp["id"] and r["selected"]}
        if actual - declared:
            raise ValueError(f"Selected records outside the declared plan: {exp['id']}")
        missing.extend({"experiment_id": exp["id"], "task_id": t, "condition": c, "repeat_id": r} for t, c, r in sorted(declared - actual))
        for condition in exp["conditions"]:
            group = [r for r in rows if r["experiment_id"] == exp["id"] and r["condition"] == condition]
            summaries.append({"experiment_id": exp["id"], "condition": condition,
                              **summarize(group, len(exp["tasks"]) * len(exp["repeat_ids"]))})
    comparisons = []
    for exp in manifest["experiments"]:
        for pair in (("A", "D"), ("C", "D")):
            if all(c in exp["conditions"] for c in pair):
                comparisons.extend({"comparison": exp["id"] + ":" + "-".join(pair), **p}
                                   for p in paired_rows(rows, [exp["id"]], [exp["id"]], pair))
    for comp in manifest.get("comparisons", []):
        if comp["candidate"]:
            comparisons.extend({"comparison": comp["id"], **p} for p in paired_rows(rows, comp["baseline"], comp["candidate"]))
    checks = [{"run_id": r["run_id"], "check": k} for r in rows for k, v in r["checks"].items() if v is False]
    for row in rows:
        for event in row["feedback"]["events"]:
            for check in ("delivery_hash_matches", "delivery_call_matches"):
                if event.get(check) is False:
                    checks.append({"run_id": row["run_id"], "event_id": event["event_id"], "check": check})
            if event["update_applied"] is True and event["delivery_found"] is not True:
                checks.append({"run_id": row["run_id"], "event_id": event["event_id"], "check": "applied_feedback_delivery"})
    cohorts = {}
    for cohort in manifest.get("cohorts", []):
        selected_rows = [r for r in rows if r["experiment_id"] in cohort["experiments"]
                         and (not cohort.get("tasks") or r["task_id"] in cohort["tasks"])]
        keys = [(r["task_id"], r["condition"], r["repeat_id"]) for r in selected_rows if r["selected"]]
        if len(keys) != len(set(keys)):
            raise ValueError("A descriptive cohort cannot double-count task/condition/repeat")
        cohorts[cohort["id"]] = {c: summarize([r for r in selected_rows if r["condition"] == c])
                                 for c in sorted({r["condition"] for r in selected_rows})}
    return {"schema_version": 1, "attempts": rows, "condition_summary": summaries,
            "comparisons": comparisons, "missing_selected": missing, "audit_failures": checks,
            "cohorts": cohorts}


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()} for row in rows)


def write_outputs(analysis: dict, destination: Path) -> None:
    if destination.exists():
        raise ValueError("Output directory already exists. Choose a fresh directory.")
    destination.mkdir(parents=True)
    (destination / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(destination / "run_summary.csv", [{k: v for k, v in row.items() if k not in {"feedback", "artifacts"}} for row in analysis["attempts"]])
    write_csv(destination / "condition_summary.csv", analysis["condition_summary"])
    write_csv(destination / "comparisons.csv", analysis["comparisons"])
    write_csv(destination / "feedback_events.csv", [{"experiment_id": row["experiment_id"], "run_id": row["run_id"], "task_id": row["task_id"], **event} for row in analysis["attempts"] for event in row["feedback"]["events"]])
    write_csv(destination / "d_timing.csv", [{"experiment_id": row["experiment_id"], "run_id": row["run_id"],
        "task_id": row["task_id"], "selected": row["selected"], "runtime_seconds": row["runtime_seconds"],
        "initial_localization_seconds": row["initial_localization_seconds"],
        "feedback_total_seconds": row["feedback_total_seconds"], **row["d_timing"]}
        for row in analysis["attempts"] if row["condition"] == "D"])


def verify_checksums(root: Path, checksum_file: Path) -> dict:
    failures = []
    count = 0
    for line in checksum_file.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = safe_path(root, relative)
        count += 1
        if not path.is_file() or sha256(path.read_bytes()) != expected:
            failures.append(relative)
    return {"checked": count, "failures": failures}
