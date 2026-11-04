#!/usr/bin/env python3
"""Select high-low pairs from fixed fitted utility inputs."""

from __future__ import annotations

import argparse

from utility_behavior_gap.constants import ACTOR_LABEL, REGISTERED_ACTORS
from utility_behavior_gap.io_utils import write_csv_rows
from utility_behavior_gap.pair_selection import select_pairs, write_selected_pairs
from utility_behavior_gap.paths import OUTPUT_INPUTS


def parse_actors(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--default-pairs-per-cell", type=int, default=80)
    parser.add_argument("--same-count-pairs-per-cell", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--actors",
        default="",
        help=(
            "Comma-separated actor ids. Default rewrites selected_pairs.csv for the paper roster. "
            "Named actors are written to selected_pairs__<actor>.csv and leave the paper file unchanged."
        ),
    )
    args = parser.parse_args()
    actors = parse_actors(args.actors)
    unknown = sorted(set(actors) - set(REGISTERED_ACTORS))
    if unknown:
        raise SystemExit(f"unknown actor ids: {', '.join(unknown)}")

    if not actors:
        write_selected_pairs(
            default_pairs_per_cell=args.default_pairs_per_cell,
            same_count_pairs_per_cell=args.same_count_pairs_per_cell,
            seed=args.seed,
        )
        print(f"wrote {OUTPUT_INPUTS / 'selected_pairs.csv'}")
        return

    for actor in actors:
        rows = select_pairs(
            default_pairs_per_cell=args.default_pairs_per_cell,
            same_count_pairs_per_cell=args.same_count_pairs_per_cell,
            seed=args.seed,
            actors=[actor],
        )
        if not rows:
            raise SystemExit(
                f"no fitted utilities for {actor} ({ACTOR_LABEL[actor]}). "
                "Import a utility overlay before selecting pairs."
            )
        path = OUTPUT_INPUTS / f"selected_pairs__{actor}.csv"
        write_csv_rows(path, rows)
        print(f"wrote {len(rows)} pairs to {path}")


if __name__ == "__main__":
    main()
