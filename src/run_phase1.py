"""Orchestrate all local Phase 1 data-foundation steps."""

from __future__ import annotations

import argparse

from profile_data import profile_data
from transform import transform_data
from validate import validate_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-profile", action="store_true")
    parser.add_argument("--skip-transform", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.skip_profile:
        profile_data()
    if not args.skip_transform:
        transform_data()
    if not args.skip_validation:
        validate_data()


if __name__ == "__main__":
    main()

