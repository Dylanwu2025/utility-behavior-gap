#!/usr/bin/env python3
"""Credible loss-frame null control: 60 wallabies vs 60 wallabies vs no prize.

Two independent samples of the same mid-animal stake (same species, same count)
should judge near chance. Also compares that stake to no_prize.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utility_behavior_gap.constants import REGISTERED_ACTORS
from utility_behavior_gap.io_utils import read_csv_rows, read_jsonl, write_jsonl
from utility_behavior_gap.job_builder import (
    common_job,
    rewritten_consequence,
    task_rows_for_task,
    write_generation_jobs,
)
from utility_behavior_gap.paths import INPUTS
from utility_behavior_gap.prompts import (
    build_essay_credible_intervention_nolimit_loss_prompt,
    build_essay_credible_no_prize_nolimit_prompt,
)


COMPARISON = "mid_same_count_nolimit_loss"
DEFAULT_ACTORS = ("kimi-k3-or",)
OUTCOME = "60 wallabies are saved from dying."
SAMPLE_A = "wallabies_60_a"
SAMPLE_B = "wallabies_60_b"


def parse_actors(raw: str) -> list[str]:
    actors = [part.strip() for part in raw.split(",") if part.strip()]
    unknown = sorted(set(actors) - set(REGISTERED_ACTORS))
    if unknown:
        raise SystemExit(f"unknown actors: {', '.join(unknown)}")
    return actors


def topics(limit: int) -> list[dict[str, str]]:
    rows = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[:limit]
    if len(rows) < limit:
        raise SystemExit(f"only {len(rows)} essay topics are available")
    for row in rows:
        row["task"] = "essay"
    return rows


def prepare_generation(limit: int, actors: list[str]) -> Path:
    consequence = rewritten_consequence(OUTCOME)
    jobs = []
    for actor in actors:
        for topic in topics(limit):
            label = topic["item_label"]
            mid_prompt = build_essay_credible_intervention_nolimit_loss_prompt(
                label, consequence, OUTCOME
            )
            arms = [
                (SAMPLE_A, "mid_a", consequence, mid_prompt),
                (SAMPLE_B, "mid_b", consequence, mid_prompt),
                (
                    "no_prize",
                    "no_prize",
                    "",
                    build_essay_credible_no_prize_nolimit_prompt(label),
                ),
            ]
            for arm_id, condition, description, prompt in arms:
                jobs.append(
                    common_job(
                        pair_uid=f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:{arm_id}",
                        comparison=COMPARISON,
                        actor=actor,
                        task_row=topic,
                        domain="animals",
                        condition_a=condition,
                        condition_b="unused",
                        prompt_a=prompt,
                        prompt_b=prompt,
                        predicted_condition=condition,
                        other_condition="unused",
                        cause_pair_label=arm_id,
                        category="no_prize" if condition == "no_prize" else "mid_same",
                        high_description=description,
                        framing="credible_grant_nolimit_loss_mid_same_count",
                        repeat="0",
                        topic_design=COMPARISON,
                        source_note="60 wallabies vs 60 wallabies null; loss frame",
                    )
                )
    manifest = write_generation_jobs(jobs)
    print(f"wrote {len(jobs)} generations to {manifest}")
    return manifest


def copied(source: dict, *, pair_uid: str, suffix: str, condition: str) -> dict:
    row = dict(source)
    row["output_id"] = f"{pair_uid}::{suffix}"
    row["pair_uid"] = pair_uid
    row["condition"] = condition
    row["copied_from_output_id"] = source["output_id"]
    return row


def bridge(manifest: Path, limit: int, actors: list[str]) -> Path:
    run_dir = manifest.parent
    generated = {
        row["pair_uid"]: row
        for row in read_jsonl(run_dir / "generations.jsonl")
        if str(row.get("output_text") or "").strip()
    }
    source_jobs = {row["pair_uid"]: row for row in read_jsonl(manifest)}
    jobs = []
    pending = []

    def require(actor: str, item: str, arm_id: str) -> tuple[dict, dict]:
        uid = f"{COMPARISON}:{actor}:essay:{item}:{arm_id}"
        row = generated.get(uid)
        job = source_jobs.get(uid)
        if row is None or job is None:
            raise SystemExit(f"missing generation {uid}")
        return job, row

    for actor in actors:
        for topic in topics(limit):
            item = f"i{topic['item_index']}"
            a_job, a_gen = require(actor, item, SAMPLE_A)
            b_job, b_gen = require(actor, item, SAMPLE_B)
            n_job, n_gen = require(actor, item, "no_prize")
            contrasts = [
                ("same_mid", a_job, a_gen, b_job, b_gen, "mid_a", "mid_b"),
                ("mid_vs_noprize", a_job, a_gen, n_job, n_gen, "mid_a", "no_prize"),
            ]
            for label, left_job, left_gen, right_job, right_gen, left_name, right_name in contrasts:
                pair_uid = f"{COMPARISON}:{actor}:essay:{item}:{label}:vs"
                jobs.append(
                    common_job(
                        pair_uid=pair_uid,
                        comparison=COMPARISON,
                        actor=actor,
                        task_row=topic,
                        domain="animals",
                        condition_a=left_name,
                        condition_b=right_name,
                        prompt_a=left_job["prompt_a"],
                        prompt_b=right_job["prompt_a"],
                        predicted_condition=left_name,
                        other_condition=right_name,
                        cause_pair_label=label,
                        category="mid_same" if label == "same_mid" else "no_prize",
                        high_description=left_job.get("high_description", ""),
                        low_description=right_job.get("high_description", ""),
                        framing="credible_grant_nolimit_loss_mid_same_count",
                        repeat="0",
                        topic_design=COMPARISON,
                        source_note="essays copied from mid-same-count generation run",
                    )
                )
                pending.append((pair_uid, "a", left_gen, left_name))
                pending.append((pair_uid, "b", right_gen, right_name))
    judge_manifest = write_generation_jobs(jobs)
    write_jsonl(
        judge_manifest.parent / "generations.jsonl",
        [
            copied(source, pair_uid=pair_uid, suffix=suffix, condition=condition)
            for pair_uid, suffix, source, condition in pending
        ],
    )
    print(f"wrote {len(jobs)} judge pairs to {judge_manifest}")
    return judge_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", type=int, default=30)
    parser.add_argument("--actors", default=",".join(DEFAULT_ACTORS))
    parser.add_argument("--bridge", type=Path, default=None)
    args = parser.parse_args()
    actors = parse_actors(args.actors)
    if args.bridge is None:
        prepare_generation(args.topics, actors)
    else:
        bridge(args.bridge, args.topics, actors)


if __name__ == "__main__":
    main()
