#!/usr/bin/env python3
"""Judge the mid-animal okay essays against the matched no-prize essays.

Both arms already exist. The no-prize essays come from the animal-versus-no-prize
run. The okay essays are the five middle-ranked animal stakes.
"""

from __future__ import annotations

import argparse

from utility_behavior_gap.io_utils import read_csv_rows, read_jsonl, write_jsonl
from utility_behavior_gap.job_builder import common_job, task_rows_for_task, write_generation_jobs
from utility_behavior_gap.paths import FOLLOWUP_INPUTS, INPUTS, ROOT
from utility_behavior_gap.prompts import build_essay_intervention_prompt, build_essay_no_prize_prompt


COMPARISONS = {
    "mid_animal": "opus48_mid_animal_vs_noprize",
    "administrative": "opus48_admin_vs_noprize",
}
ACTOR = "claude-opus-4.8-or"
OKAY_RUN = (
    ROOT
    / "outputs/api/runs"
    / "essay__opus48_animals_vs_okay__claude-opus-4.8-or__2026-10-12_05-57-45Z__hash-102f48551b61"
)
NOPRIZE_RUN = (
    ROOT
    / "outputs/api/runs"
    / "essay__opus48_animals_vs_noprize__claude-opus-4.8-or__2026-10-12_05-51-54Z__hash-156234fd7b55"
)


def copied(source: dict, *, pair_uid: str, suffix: str, condition: str) -> dict:
    row = dict(source)
    row["output_id"] = f"{pair_uid}::{suffix}"
    row["pair_uid"] = pair_uid
    row["condition"] = condition
    row["copied_from_output_id"] = source["output_id"]
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=sorted(COMPARISONS), default="mid_animal")
    args = parser.parse_args()
    comparison = COMPARISONS[args.family]
    topics = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[:30]
    for topic in topics:
        topic["task"] = "essay"
    okays = [
        row
        for row in read_csv_rows(FOLLOWUP_INPUTS / "crossdomain_okay_outcomes.csv")
        if row["outcome_family"] == args.family
    ]
    no_prize = {
        row["pair_uid"].split(":")[3]: row
        for row in read_jsonl(NOPRIZE_RUN / "generations.jsonl")
        if row.get("condition") == "no_prize"
    }
    okay_gens = {
        row["pair_uid"]: row
        for row in read_jsonl(OKAY_RUN / "generations.jsonl")
        if row.get("condition") == "okay"
    }
    jobs = []
    pending = []
    for topic in topics:
        item = f"i{topic['item_index']}"
        plain = no_prize.get(item)
        if plain is None or not str(plain.get("output_text") or "").strip():
            raise SystemExit(f"missing no-prize essay for {item}")
        plain_prompt = build_essay_no_prize_prompt(topic["item_label"])
        for okay in okays:
            okay_uid = f"opus48_animals_vs_okay:{ACTOR}:essay:{item}:{okay['outcome_id']}"
            okay_gen = okay_gens.get(okay_uid)
            if okay_gen is None or not str(okay_gen.get("output_text") or "").strip():
                raise SystemExit(f"missing okay essay {okay_uid}")
            pair_uid = f"{comparison}:{ACTOR}:essay:{item}:{okay['outcome_id']}"
            jobs.append(
                common_job(
                    pair_uid=pair_uid,
                    comparison=comparison,
                    actor=ACTOR,
                    task_row=topic,
                    domain="animals",
                    condition_a="no_prize",
                    condition_b="okay",
                    prompt_a=plain_prompt,
                    prompt_b=build_essay_intervention_prompt(topic["item_label"], okay["consequence"]),
                    predicted_condition="no_prize",
                    other_condition="okay",
                    cause_pair_label=okay["outcome_id"],
                    category=okay["outcome_family"],
                    low_description=okay["description"],
                    framing=f"{args.family}_vs_no_prize",
                    repeat="0",
                    topic_design=comparison,
                    source_note="both essays copied; no new generation",
                )
            )
            pending.append((pair_uid, "a", plain, "no_prize"))
            pending.append((pair_uid, "b", okay_gen, "okay"))
    manifest = write_generation_jobs(jobs)
    stamped = {job["pair_uid"]: job for job in read_jsonl(manifest)}
    generations = [
        copied(source, pair_uid=pair_uid, suffix=suffix, condition=condition)
        for pair_uid, suffix, source, condition in pending
    ]
    write_jsonl(manifest.parent / "generations.jsonl", generations)
    print(f"wrote {len(stamped)} judge pairs to {manifest}")


if __name__ == "__main__":
    main()
