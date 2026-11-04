#!/usr/bin/env python3
"""Add the paper's max-effort cue to the lives-screen no-prize prompt.

Generation writes one exhortation essay per topic and actor. ``--bridge``
then pairs that essay with the lives, mid-animal, and no-prize essays already
generated for the same topic, and also pairs the mid-animal essay with the
no-prize essay. Existing lives-versus-cat and lives-versus-empty judgments
are left in the source run.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utility_behavior_gap.constants import EXPANSION_ACTORS
from utility_behavior_gap.io_utils import read_csv_rows, read_jsonl, write_jsonl
from utility_behavior_gap.job_builder import (
    clean_essay_direct_prompt,
    common_job,
    task_rows_for_task,
    write_generation_jobs,
)
from utility_behavior_gap.paths import INPUTS, OUTPUT_API
from utility_behavior_gap.prompts import (
    MAX_EFFORT_STRONG_SYSTEM_PROMPTS,
    build_modgrid_empty_prompt,
    build_modgrid_fund_prompt,
)


COMPARISON = "lives_exhortation_screen"
SOURCE_COMPARISON = "lives_mundane_screen"
LIVES = "60 humans are saved from dying."
MID_ANIMAL = "2 cats are saved from dying."
EXHORTATION = "exhortation"
EMPTY = "framed_empty"
LIVES_CONDITION = "lives"
MID = "mid_animal"

# condition_a, condition_b, predicted side, where to read each side.
CONTRASTS = (
    ("exhortation_vs_empty", EXHORTATION, EMPTY, EXHORTATION),
    ("exhortation_vs_lives", EXHORTATION, LIVES_CONDITION, EXHORTATION),
    ("exhortation_vs_mid_animal", EXHORTATION, MID, EXHORTATION),
    ("mid_animal_vs_empty", MID, EMPTY, MID),
)


def exhortation_prompt(task_block: str) -> str:
    empty = build_modgrid_empty_prompt("essay", task_block)
    cue = MAX_EFFORT_STRONG_SYSTEM_PROMPTS["essay"]
    return f"{empty}\n\n{cue}"


def latest_source_run() -> Path:
    runs = sorted((OUTPUT_API / "runs").glob(f"essay__{SOURCE_COMPARISON}__*"))
    if not runs:
        raise SystemExit(f"no {SOURCE_COMPARISON} run found")
    return runs[-1]


def prepare_generation(actors: list[str], topics: list[dict[str, str]]) -> Path:
    jobs = []
    for topic in topics:
        task_block = clean_essay_direct_prompt(str(topic["item_label"]))
        prompt = exhortation_prompt(task_block)
        empty = build_modgrid_empty_prompt("essay", task_block)
        for actor in actors:
            jobs.append(
                common_job(
                    pair_uid=f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:exhortation",
                    comparison=COMPARISON,
                    actor=actor,
                    task_row=topic,
                    domain="",
                    condition_a=EXHORTATION,
                    condition_b=EMPTY,
                    prompt_a=prompt,
                    prompt_b=empty,
                    predicted_condition=EXHORTATION,
                    other_condition=EMPTY,
                    cause_pair_label="exhortation_only",
                    good_text=MAX_EFFORT_STRONG_SYSTEM_PROMPTS["essay"],
                    bad_text="",
                    framing="empty_plus_max_effort",
                    repeat="0",
                    topic_design=COMPARISON,
                    source_note="max-effort cue appended to the no-prize competition prompt",
                )
            )
    manifest = write_generation_jobs(jobs)
    print(f"wrote {len(jobs)} exhortation jobs to {manifest}")
    return manifest


def index_source_outputs(run_dir: Path) -> dict[tuple[str, str, str], dict]:
    jobs = read_jsonl(run_dir / "generation_jobs.jsonl")
    generations = {row["output_id"]: row for row in read_jsonl(run_dir / "generations.jsonl")}
    indexed: dict[tuple[str, str, str], dict] = {}
    for job in jobs:
        for suffix, condition in (("a", job["condition_a"]), ("b", job["condition_b"])):
            row = generations.get(f"{job['pair_uid']}::{suffix}")
            if row is None:
                raise SystemExit(f"missing source generation {job['pair_uid']}::{suffix}")
            # The lives arm was sampled twice. Keep the lives-versus-empty sample
            # so lives, empty, and exhortation are the same essays.
            if condition == LIVES_CONDITION and job["cause_pair_label"] != "lives_vs_empty":
                continue
            indexed[(job["actor"], str(job["item_index"]), condition)] = row
    return indexed


def source_output(indexed: dict[tuple[str, str, str], dict], actor: str, item_index: str, condition: str) -> dict:
    key = (actor, item_index, condition)
    row = indexed.get(key)
    if row is None:
        raise SystemExit(f"missing source output for {key}")
    return row


def copied_generation(source: dict, *, job: dict, suffix: str, condition: str) -> dict:
    row = dict(source)
    row["output_id"] = f"{job['pair_uid']}::{suffix}"
    row["pair_uid"] = job["pair_uid"]
    row["condition"] = condition
    row["copied_from_output_id"] = source["output_id"]
    return row


def bridge(exhortation_manifest: Path, actors: list[str], topics: list[dict[str, str]]) -> Path:
    exhort_dir = exhortation_manifest.parent
    exhort_jobs = {job["pair_uid"]: job for job in read_jsonl(exhortation_manifest)}
    exhort_gens = {row["output_id"]: row for row in read_jsonl(exhort_dir / "generations.jsonl")}
    source = index_source_outputs(latest_source_run())
    # Lives and empty come from the lives-versus-empty pair so those three arms share essays.
    jobs = []
    pending_copies: list[tuple[dict, str, str, dict]] = []
    for topic in topics:
        task_block = clean_essay_direct_prompt(str(topic["item_label"]))
        prompts = {
            EXHORTATION: exhortation_prompt(task_block),
            EMPTY: build_modgrid_empty_prompt("essay", task_block),
            LIVES_CONDITION: build_modgrid_fund_prompt("essay", task_block, target=LIVES),
            MID: build_modgrid_fund_prompt("essay", task_block, target=MID_ANIMAL),
        }
        for actor in actors:
            exhort_uid = f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:exhortation"
            exhort_row = exhort_gens.get(f"{exhort_uid}::a")
            if exhort_row is None or not str(exhort_row.get("output_text", "")).strip():
                raise SystemExit(f"missing exhortation generation {exhort_uid}")
            if exhort_uid not in exhort_jobs:
                raise SystemExit(f"missing exhortation job {exhort_uid}")
            arms = {
                EXHORTATION: exhort_row,
                LIVES_CONDITION: source_output(source, actor, str(topic["item_index"]), LIVES_CONDITION),
                MID: source_output(source, actor, str(topic["item_index"]), MID),
                EMPTY: source_output(source, actor, str(topic["item_index"]), EMPTY),
            }
            for label, condition_a, condition_b, predicted in CONTRASTS:
                job = common_job(
                    pair_uid=f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:{label}",
                    comparison=COMPARISON,
                    actor=actor,
                    task_row=topic,
                    domain="animals" if MID in (condition_a, condition_b) and EMPTY not in (condition_a, condition_b) else "",
                    condition_a=condition_a,
                    condition_b=condition_b,
                    prompt_a=prompts[condition_a],
                    prompt_b=prompts[condition_b],
                    predicted_condition=predicted,
                    other_condition=condition_b if predicted == condition_a else condition_a,
                    cause_pair_label=label,
                    good_text=LIVES if LIVES_CONDITION in (condition_a, condition_b) else "",
                    bad_text=MID_ANIMAL if MID in (condition_a, condition_b) else "",
                    framing="four_arm_screen",
                    repeat="0",
                    topic_design=COMPARISON,
                    source_note="exhortation is the no-prize prompt plus the max-effort cue; other arms are copied",
                )
                jobs.append(job)
                pending_copies.append((job, "a", condition_a, arms[condition_a]))
                pending_copies.append((job, "b", condition_b, arms[condition_b]))

    manifest = write_generation_jobs(jobs)
    stamped = read_jsonl(manifest)
    by_uid = {job["pair_uid"]: job for job in stamped}
    generations = []
    for job, suffix, condition, source_row in pending_copies:
        generations.append(copied_generation(source_row, job=by_uid[job["pair_uid"]], suffix=suffix, condition=condition))
    write_jsonl(manifest.parent / "generations.jsonl", generations)
    print(f"wrote {len(stamped)} bridge pairs and {len(generations)} copied generations to {manifest}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actors", default=",".join(EXPANSION_ACTORS))
    parser.add_argument("--topics", type=int, default=4)
    parser.add_argument(
        "--bridge",
        type=Path,
        default=None,
        help="Exhortation generation manifest. Copies arms into a judging run.",
    )
    args = parser.parse_args()
    actors = [item.strip() for item in args.actors.split(",") if item.strip()]
    topics = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[: args.topics]
    if len(topics) < args.topics:
        raise SystemExit(f"only {len(topics)} essay topics are available")
    if args.bridge is None:
        prepare_generation(actors, topics)
    else:
        bridge(args.bridge, actors, topics)


if __name__ == "__main__":
    main()
