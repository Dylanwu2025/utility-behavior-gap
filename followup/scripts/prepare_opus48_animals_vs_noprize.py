#!/usr/bin/env python3
"""Opus 4.8 animal high stake versus a matched no-prize essay.

The high stake is the same one used in the Opus reasoning screen: sixty
humans saved. Reasoning stays on at generation time.
"""

from __future__ import annotations

import argparse

from utility_behavior_gap.io_utils import read_csv_rows
from utility_behavior_gap.job_builder import (
    common_job,
    highlow_intervention_prompt,
    rewritten_consequence,
    task_rows_for_task,
    write_generation_jobs,
)
from utility_behavior_gap.paths import INPUTS
from utility_behavior_gap.prompts import build_essay_no_prize_prompt


COMPARISON = "opus48_animals_vs_noprize"
ACTOR = "claude-opus-4.8-or"
HIGH_OUTCOME = "60 humans are saved from dying."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", type=int, default=30)
    args = parser.parse_args()
    rows = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[: args.topics]
    if len(rows) < args.topics:
        raise SystemExit(f"only {len(rows)} essay topics are available")
    high_description = rewritten_consequence(HIGH_OUTCOME)
    jobs = []
    for topic in rows:
        topic["task"] = "essay"
        jobs.append(
            common_job(
                pair_uid=f"{COMPARISON}:{ACTOR}:essay:i{topic['item_index']}:animals",
                comparison=COMPARISON,
                actor=ACTOR,
                task_row=topic,
                domain="animals",
                condition_a="high",
                condition_b="no_prize",
                prompt_a=highlow_intervention_prompt(topic, HIGH_OUTCOME),
                prompt_b=build_essay_no_prize_prompt(topic["item_label"]),
                predicted_condition="high",
                other_condition="no_prize",
                cause_pair_label="humans_vs_noprize",
                high_description=high_description,
                framing="animals_vs_no_prize",
                repeat="0",
                topic_design=COMPARISON,
                source_note="high stake is sixty humans saved; no-prize omits the funded policy",
            )
        )
    manifest = write_generation_jobs(jobs)
    print(f"wrote {len(jobs)} pairs to {manifest}")


if __name__ == "__main__":
    main()
