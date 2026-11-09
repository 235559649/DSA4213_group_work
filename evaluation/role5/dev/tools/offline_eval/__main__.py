"""Run with: python -m tools.offline_eval --help."""
import argparse
import json
from pathlib import Path

from .core import analyze, verify_checksums, write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze existing experiment artifacts without running agents or tests.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("analyze", help="Recompute metrics from an explicit manifest")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True, help="A new output directory")
    verify = commands.add_parser("verify", help="Verify the staged file checksums")
    verify.add_argument("--root", type=Path, default=Path("."))
    verify.add_argument("--checksums", type=Path, default=Path("CHECKSUMS.sha256"))
    args = parser.parse_args()
    try:
        if args.command == "verify":
            result = verify_checksums(args.root.resolve(), args.checksums)
            print(json.dumps(result, indent=2))
            return int(bool(result["failures"]))
        result = analyze(args.manifest.resolve())
        write_outputs(result, args.output.resolve())
        print(json.dumps({"attempts": len(result["attempts"]), "selected": sum(r["selected"] for r in result["attempts"]),
                          "missing_selected": len(result["missing_selected"]), "audit_failures": result["audit_failures"]}, indent=2))
        return int(bool(result["audit_failures"]))
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
