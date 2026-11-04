#!/usr/bin/env python3
"""Prepare a small essay screen with fixed good-versus-bad prizes.

This does not fit utilities. Each pair uses the paper's fund-intervention
wording and two outcomes already ranked as obvious opposites by the published
models. Default size is 4 essay topics x 2 cause pairs x the expansion actors.
"""

from __future__ import annotations

import argparse

from utility_behavior_gap.constants import EXPANSION_ACTORS
from utility_behavior_gap.io_utils import read_csv_rows
from utility_behavior_gap.job_builder import (
    clean_essay_direct_prompt,
    common_job,
    task_rows_for_task,
    write_generation_jobs,
)
from utility_behavior_gap.paths import INPUTS
from utility_behavior_gap.prompts import build_modgrid_fund_prompt


COMPARISON = "obvious_preference_screen"
CAUSE_LABELS = ("labor_03", "civil_rights_03")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actors", default=",".join(EXPANSION_ACTORS))
    parser.add_argument("--topics", type=int, default=4)
    parser.add_argument("--causes", default=",".join(CAUSE_LABELS))
    args = parser.parse_args()

    actors = [item.strip() for item in args.actors.split(",") if item.strip()]
    cause_labels = [item.strip() for item in args.causes.split(",") if item.strip()]
    causes = {row["cause_pair_label"]: row for row in read_csv_rows(INPUTS / "moral_cause_pairs.csv")}
    missing = [label for label in cause_labels if label not in causes]
    if missing:
        raise SystemExit(f"unknown cause pairs: {', '.join(missing)}")
    topics = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[: args.topics]
    if len(topics) < args.topics:
        raise SystemExit(f"only {len(topics)} essay topics are available")

    jobs = []
    for topic in topics:
        task_block = clean_essay_direct_prompt(str(topic["item_label"]))
        for label in cause_labels:
            cause = causes[label]
            for actor in actors:
                jobs.append(
                    common_job(
                        pair_uid=(
                            f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:{label}"
                        ),
                        comparison=COMPARISON,
                        actor=actor,
                        task_row=topic,
                        domain="",
                        condition_a="moral_good",
                        condition_b="moral_bad",
                        prompt_a=build_modgrid_fund_prompt("essay", task_block, target=cause["good_text"]),
                        prompt_b=build_modgrid_fund_prompt("essay", task_block, target=cause["bad_text"]),
                        predicted_condition="moral_good",
                        other_condition="moral_bad",
                        cause_pair_label=label,
                        good_text=cause["good_text"],
                        bad_text=cause["bad_text"],
                        framing="funded_intervention",
                        repeat="0",
                        topic_design="obvious_preference_screen",
                    )
                )

    manifest = write_generation_jobs(jobs)
    print(f"wrote {len(jobs)} pairs ({len(jobs) * 2} generations) to {manifest}")


if __name__ == "__main__":
    main()
