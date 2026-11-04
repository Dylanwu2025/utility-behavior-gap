#!/usr/bin/env python3
"""Judge Opus 4.8's high animal essays against the cross-domain okay stakes.

Reuses the 30 high essays from the animal-versus-no-prize run. Each topic is
rewritten once for every okay outcome in crossdomain_okay_outcomes.csv.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utility_behavior_gap.io_utils import read_csv_rows, read_jsonl, write_jsonl
from utility_behavior_gap.job_builder import common_job, task_rows_for_task, write_generation_jobs
from utility_behavior_gap.paths import FOLLOWUP_INPUTS, INPUTS, ROOT
from utility_behavior_gap.prompts import build_essay_intervention_prompt


COMPARISON = "opus48_animals_vs_okay"
ACTOR = "claude-opus-4.8-or"
OKAY_PATH = FOLLOWUP_INPUTS / "crossdomain_okay_outcomes.csv"
HIGH_RUN = (
    ROOT
    / "outputs/api/runs"
    / "essay__opus48_animals_vs_noprize__claude-opus-4.8-or__2026-10-12_05-51-54Z__hash-156234fd7b55"
)
HIGH_COMPARISON = "opus48_animals_vs_noprize"


def topics(limit: int) -> list[dict[str, str]]:
    rows = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[:limit]
    if len(rows) < limit:
        raise SystemExit(f"only {len(rows)} essay topics are available")
    for row in rows:
        row["task"] = "essay"
    return rows


def okay_rows() -> list[dict[str, str]]:
    rows = read_csv_rows(OKAY_PATH)
    if not rows:
        raise SystemExit(f"no outcomes in {OKAY_PATH}")
    return rows


def prepare_generation(limit: int) -> Path:
    jobs = []
    for topic in topics(limit):
        for okay in okay_rows():
            prompt = build_essay_intervention_prompt(topic["item_label"], okay["consequence"])
            jobs.append(
                common_job(
                    pair_uid=(
                        f"{COMPARISON}:{ACTOR}:essay:i{topic['item_index']}:{okay['outcome_id']}"
                    ),
                    comparison=COMPARISON,
                    actor=ACTOR,
                    task_row=topic,
                    domain="animals",
                    condition_a="okay",
                    condition_b="unused",
                    prompt_a=prompt,
                    prompt_b=prompt,
                    predicted_condition="okay",
                    other_condition="unused",
                    cause_pair_label=okay["outcome_id"],
                    category=okay["outcome_family"],
                    high_description=okay["description"],
                    framing="okay_anchor",
                    repeat="0",
                    topic_design=COMPARISON,
                    source_note=okay["selection_basis"],
                )
            )
    manifest = write_generation_jobs(jobs)
    print(f"wrote {len(jobs)} okay generations to {manifest}")
    return manifest


def copied_generation(source: dict, *, pair_uid: str, suffix: str, condition: str) -> dict:
    row = dict(source)
    row["output_id"] = f"{pair_uid}::{suffix}"
    row["pair_uid"] = pair_uid
    row["condition"] = condition
    row["copied_from_output_id"] = source["output_id"]
    return row


def bridge(manifest: Path, limit: int) -> Path:
    run_dir = manifest.parent
    high_jobs = {row["pair_uid"]: row for row in read_jsonl(HIGH_RUN / "generation_jobs.jsonl")}
    high_gens = [
        row
        for row in read_jsonl(HIGH_RUN / "generations.jsonl")
        if row.get("condition") == "high" and row.get("actor") == ACTOR
    ]
    high_by_item = {}
    for row in high_gens:
        item = row["pair_uid"].split(":")[-2]
        high_by_item[item] = row
    generated = {row["output_id"]: row for row in read_jsonl(run_dir / "generations.jsonl")}
    jobs = []
    pending: list[tuple[str, str, dict]] = []
    for topic in topics(limit):
        item = f"i{topic['item_index']}"
        high = high_by_item.get(item)
        high_uid = f"{HIGH_COMPARISON}:{ACTOR}:essay:{item}:animals"
        high_job = high_jobs.get(high_uid)
        if high is None or high_job is None or not str(high.get("output_text") or "").strip():
            raise SystemExit(f"missing high essay for {item}")
        for okay in okay_rows():
            okay_uid = f"{COMPARISON}:{ACTOR}:essay:{item}:{okay['outcome_id']}"
            okay_gen = generated.get(f"{okay_uid}::a")
            if okay_gen is None or not str(okay_gen.get("output_text") or "").strip():
                raise SystemExit(f"missing okay generation {okay_uid}")
            pair_uid = f"{COMPARISON}:{ACTOR}:essay:{item}:{okay['outcome_id']}:high_vs_okay"
            prompt = build_essay_intervention_prompt(topic["item_label"], okay["consequence"])
            jobs.append(
                common_job(
                    pair_uid=pair_uid,
                    comparison=COMPARISON,
                    actor=ACTOR,
                    task_row=topic,
                    domain="animals",
                    condition_a="high",
                    condition_b="okay",
                    prompt_a=high_job["prompt_a"],
                    prompt_b=prompt,
                    predicted_condition="high",
                    other_condition="okay",
                    cause_pair_label=okay["outcome_id"],
                    category=okay["outcome_family"],
                    high_description=high_job.get("high_description", ""),
                    low_description=okay["description"],
                    framing="animals_high_vs_okay",
                    repeat="0",
                    topic_design=COMPARISON,
                    source_note="high essay copied from the animal-versus-no-prize run",
                )
            )
            pending.append((pair_uid, "a", high))
            pending.append((pair_uid, "b", okay_gen))
    judge_manifest = write_generation_jobs(jobs)
    stamped = {job["pair_uid"]: job for job in read_jsonl(judge_manifest)}
    generations = [
        copied_generation(
            source,
            pair_uid=pair_uid,
            suffix=suffix,
            condition=stamped[pair_uid]["condition_a" if suffix == "a" else "condition_b"],
        )
        for pair_uid, suffix, source in pending
    ]
    write_jsonl(judge_manifest.parent / "generations.jsonl", generations)
    print(f"wrote {len(stamped)} judge pairs to {judge_manifest}")
    return judge_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", type=int, default=30)
    parser.add_argument("--bridge", type=Path, default=None)
    args = parser.parse_args()
    if args.bridge is None:
        prepare_generation(args.topics)
    else:
        bridge(args.bridge, args.topics)


if __name__ == "__main__":
    main()
