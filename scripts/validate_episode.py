#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from rexrov_single_oberon7_fm_dp.dataset_writer import validate_episode_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Stage 4 DP/FM episode .npz file.")
    parser.add_argument("episode", help="Path to an episode .npz file")
    parser.add_argument(
        "--strict-nan",
        action="store_true",
        help="Fail on NaN even when metadata marks a field unavailable.",
    )
    args = parser.parse_args()

    result = validate_episode_file(
        args.episode,
        allow_unavailable_nan=not args.strict_nan,
    )

    status = "PASS" if result.ok else "FAIL"
    print(f"validation: {status}")
    for key, value in result.summary.items():
        print(f"{key}: {value}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
