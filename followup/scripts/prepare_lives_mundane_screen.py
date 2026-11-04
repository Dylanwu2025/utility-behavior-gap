#!/usr/bin/env python3
"""Prepare an essay screen for lives saved versus a mundane prize and no prize.

The high prize and the mid-animal prize are published utility-option texts.
The empty arm uses the paper's competition frame with no funded outcome.
This does not fit utilities.
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
from utility_behavior_gap.prompts import build_modgrid_empty_prompt, build_modgrid_fund_prompt


COMPARISON = "lives_mundane_screen"
LIVES = "60 humans are saved from dying."
MID_ANIMAL = "2 cats are saved from dying."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actors", default=",".join(EXPANSION_ACTORS))
    parser.add_argument("--topics", type=int, default=4)
    args = parser.parse_args()

    actors = [item.strip() for item in args.actors.split(",") if item.strip()]
    topics = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[: args.topics]
    if len(topics) < args.topics:
        raise SystemExit(f"only {len(topics)} essay topics are available")

    jobs = []
    for topic in topics:
        task_block = clean_essay_direct_prompt(str(topic["item_label"]))
        lives_prompt = build_modgrid_fund_prompt("essay", task_block, target=LIVES)
        animal_prompt = build_modgrid_fund_prompt("essay", task_block, target=MID_ANIMAL)
        empty_prompt = build_modgrid_empty_prompt("essay", task_block)
        for actor in actors:
            jobs.append(
                common_job(
                    pair_uid=f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:lives_vs_mid_animal",
                    comparison=COMPARISON,
                    actor=actor,
                    task_row=topic,
                    domain="animals",
                    condition_a="lives",
                    condition_b="mid_animal",
                    prompt_a=lives_prompt,
                    prompt_b=animal_prompt,
                    predicted_condition="lives",
                    other_condition="mid_animal",
                    cause_pair_label="lives_vs_mid_animal",
                    good_text=LIVES,
                    bad_text=MID_ANIMAL,
                    framing="funded_intervention",
                    repeat="0",
                    topic_design="lives_mundane_screen",
                )
            )
            jobs.append(
                common_job(
                    pair_uid=f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:lives_vs_empty",
                    comparison=COMPARISON,
                    actor=actor,
                    task_row=topic,
                    domain="",
                    condition_a="lives",
                    condition_b="framed_empty",
                    prompt_a=lives_prompt,
                    prompt_b=empty_prompt,
                    predicted_condition="lives",
                    other_condition="framed_empty",
                    cause_pair_label="lives_vs_empty",
                    good_text=LIVES,
                    bad_text="",
                    framing="funded_intervention_vs_empty",
                    repeat="0",
                    topic_design="lives_mundane_screen",
                )
            )

    manifest = write_generation_jobs(jobs)
    print(f"wrote {len(jobs)} pairs ({len(jobs) * 2} generations) to {manifest}")


if __name__ == "__main__":
    main()
