"""Local JSON command for the deterministic readiness assistant."""

import argparse
import json

from .assistant import InvalidIncident, run_incident


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnose a fictional readiness snapshot")
    parser.add_argument("--mode", choices=("deterministic",), default="deterministic")
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--scenario", choices=("not_ready", "healthy", "incomplete"), required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--pod", required=True)
    parser.add_argument("--service", required=True)
    options = vars(parser.parse_args(argv))
    options.pop("mode")
    try:
        report = run_incident(options)
    except InvalidIncident as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, allow_nan=False))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
