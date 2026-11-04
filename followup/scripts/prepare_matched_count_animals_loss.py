#!/usr/bin/env python3
"""Matched-count animal loss-frame screen: 60 humans vs 60 of each mid animal.

Removes the 60-vs-2 quantity confound from the earlier mid-animal design.
Default actors: Kimi, GLM-5.3, Opus 4.8 (cells that previously looked preference-shaped).
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


COMPARISON = "matched_count_animals_nolimit_loss"
DEFAULT_ACTORS = ("kimi-k3-or", "glm-5.3-or", "claude-opus-4.8-or")
HIGH_OUTCOME = "60 humans are saved from dying."
MID_SPECIES = ("wallabies", "zebras", "octopuses", "kangaroos", "lions")


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


def mid_outcomes() -> list[dict[str, str]]:
    out = []
    for species in MID_SPECIES:
        description = f"60 {species} are saved from dying."
        out.append(
            {
                "outcome_id": f"animal_{species}_60",
                "description": description,
                "consequence": rewritten_consequence(description),
            }
        )
    return out


def prepare_generation(limit: int, actors: list[str]) -> Path:
    high_consequence = rewritten_consequence(HIGH_OUTCOME)
    mids = mid_outcomes()
    jobs = []
    for actor in actors:
        for topic in topics(limit):
            label = topic["item_label"]
            arms = [
                (
                    "high",
                    "high",
                    high_consequence,
                    build_essay_credible_intervention_nolimit_loss_prompt(
                        label, high_consequence, HIGH_OUTCOME
                    ),
                ),
                (
                    "no_prize",
                    "no_prize",
                    "",
                    build_essay_credible_no_prize_nolimit_prompt(label),
                ),
            ]
            for mid in mids:
                arms.append(
                    (
                        mid["outcome_id"],
                        "okay",
                        mid["consequence"],
                        build_essay_credible_intervention_nolimit_loss_prompt(
                            label, mid["consequence"], mid["description"]
                        ),
                    )
                )
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
                        category="no_prize" if condition == "no_prize" else "mid_animal",
                        high_description=description,
                        framing="credible_grant_nolimit_loss_matched_count",
                        repeat="0",
                        topic_design=COMPARISON,
                        source_note="60 humans vs 60 mid animals; loss frame",
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
    mids = mid_outcomes()
    jobs = []
    pending = []
    skipped = []

    def require(actor: str, item: str, arm_id: str) -> tuple[dict, dict] | None:
        uid = f"{COMPARISON}:{actor}:essay:{item}:{arm_id}"
        row = generated.get(uid)
        job = source_jobs.get(uid)
        if row is None or job is None:
            skipped.append(uid)
            return None
        return job, row

    for actor in actors:
        for topic in topics(limit):
            item = f"i{topic['item_index']}"
            high_pair = require(actor, item, "high")
            plain_pair = require(actor, item, "no_prize")
            if high_pair is None or plain_pair is None:
                continue
            high_job, high = high_pair
            plain_job, plain = plain_pair
            contrasts = [("no_prize", plain_job, plain, "high", "no_prize")]
            for mid in mids:
                mid_pair = require(actor, item, mid["outcome_id"])
                if mid_pair is None:
                    continue
                mid_job, mid_gen = mid_pair
                contrasts.append((mid["outcome_id"], mid_job, mid_gen, "high", "okay"))
                contrasts.append(
                    (f"{mid['outcome_id']}_vs_noprize", mid_job, mid_gen, "no_prize", "okay")
                )
            for label, other_job, other_gen, left_name, right_name in contrasts:
                left_gen = high if left_name == "high" else plain
                left_job = high_job if left_name == "high" else plain_job
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
                        prompt_b=other_job["prompt_a"],
                        predicted_condition=left_name,
                        other_condition=right_name,
                        cause_pair_label=label,
                        category="no_prize" if label == "no_prize" else "mid_animal",
                        high_description=high_job.get("high_description", ""),
                        low_description=other_job.get("high_description", ""),
                        framing="credible_grant_nolimit_loss_matched_count",
                        repeat="0",
                        topic_design=COMPARISON,
                        source_note="essays copied from matched-count generation run",
                    )
                )
                pending.append((pair_uid, "a", left_gen, left_name))
                pending.append((pair_uid, "b", other_gen, right_name))
    judge_manifest = write_generation_jobs(jobs)
    write_jsonl(
        judge_manifest.parent / "generations.jsonl",
        [
            copied(source, pair_uid=pair_uid, suffix=suffix, condition=condition)
            for pair_uid, suffix, source, condition in pending
        ],
    )
    if skipped:
        print(f"skipped {len(set(skipped))} missing generations")
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
