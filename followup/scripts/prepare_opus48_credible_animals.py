#!/usr/bin/env python3
"""Opus 4.8 essays under the more credible grant rule.

High stake: 60 humans saved. Comparison stakes: the five middle-ranked
animals. A matched no-prize essay uses the same contest wording without a grant.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utility_behavior_gap.constants import OPEN_WEIGHT_ACTORS, REGISTERED_ACTORS
from utility_behavior_gap.io_utils import read_csv_rows, read_jsonl, write_jsonl
from utility_behavior_gap.job_builder import (
    common_job,
    rewritten_consequence,
    task_rows_for_task,
    write_generation_jobs,
)
from utility_behavior_gap.paths import FOLLOWUP_INPUTS, INPUTS
from utility_behavior_gap.prompts import (
    build_essay_credible_intervention_nolimit_loss_prompt,
    build_essay_credible_intervention_nolimit_prompt,
    build_essay_credible_intervention_prompt,
    build_essay_credible_no_prize_nolimit_prompt,
    build_essay_credible_no_prize_prompt,
)


ACTOR = "claude-opus-4.8-or"
HIGH_OUTCOME = "60 humans are saved from dying."
WORD_LIMIT_COMPARISON = "opus48_credible_animals"
NOLIMIT_COMPARISON = "opus48_credible_animals_nolimit"
NOLIMIT_LOSS_COMPARISON = "opus48_credible_animals_nolimit_loss"
OPENWEIGHT_NOLIMIT_COMPARISON = "openweight_credible_animals_nolimit"
OPENWEIGHT_NOLIMIT_LOSS_COMPARISON = "openweight_credible_animals_nolimit_loss"


def comparison_name(no_word_limit: bool, actors: list[str], *, loss_frame: bool) -> str:
    if loss_frame and not no_word_limit:
        raise SystemExit("loss-frame runs use --no-word-limit")
    if actors == [ACTOR]:
        if loss_frame:
            return NOLIMIT_LOSS_COMPARISON
        return NOLIMIT_COMPARISON if no_word_limit else WORD_LIMIT_COMPARISON
    if not no_word_limit:
        raise SystemExit("open-weight runs use the no-word-limit credible prompt")
    return OPENWEIGHT_NOLIMIT_LOSS_COMPARISON if loss_frame else OPENWEIGHT_NOLIMIT_COMPARISON


def parse_actors(raw: str) -> list[str]:
    if raw == "open-weight":
        return list(OPEN_WEIGHT_ACTORS)
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


def mid_animals() -> list[dict[str, str]]:
    rows = [
        row
        for row in read_csv_rows(FOLLOWUP_INPUTS / "crossdomain_okay_outcomes.csv")
        if row["outcome_family"] == "mid_animal"
    ]
    if len(rows) != 5:
        raise SystemExit(f"expected 5 mid-animal outcomes, found {len(rows)}")
    return rows


def prepare_generation(
    limit: int,
    *,
    no_word_limit: bool,
    actors: list[str],
    loss_frame: bool,
    repeats: int,
) -> Path:
    if repeats < 1:
        raise SystemExit("--repeats must be at least 1")
    comparison = comparison_name(no_word_limit, actors, loss_frame=loss_frame)
    no_prize_prompt = (
        build_essay_credible_no_prize_nolimit_prompt
        if no_word_limit
        else build_essay_credible_no_prize_prompt
    )
    high_consequence = rewritten_consequence(HIGH_OUTCOME)

    def intervention_prompt(topic_label: str, consequence: str, saved_description: str) -> str:
        if loss_frame:
            return build_essay_credible_intervention_nolimit_loss_prompt(
                topic_label, consequence, saved_description
            )
        if no_word_limit:
            return build_essay_credible_intervention_nolimit_prompt(topic_label, consequence)
        return build_essay_credible_intervention_prompt(topic_label, consequence)

    framing = (
        "credible_grant_nolimit_loss"
        if loss_frame
        else ("credible_grant_nolimit" if no_word_limit else "credible_grant")
    )
    source_note = (
        "grant unpaid means those who would have been saved will die"
        if loss_frame
        else "grant is reserved and paid only if this essay wins"
    )
    jobs = []
    for actor in actors:
        for topic in topics(limit):
            label = topic["item_label"]
            arms = [
                (
                    "high",
                    "high",
                    high_consequence,
                    intervention_prompt(label, high_consequence, HIGH_OUTCOME),
                )
            ]
            arms.append(("no_prize", "no_prize", "", no_prize_prompt(label)))
            for okay in mid_animals():
                arms.append(
                    (
                        okay["outcome_id"],
                        "okay",
                        okay["consequence"],
                        intervention_prompt(label, okay["consequence"], okay["description"]),
                    )
                )
            for rep in range(repeats):
                for arm_id, condition, description, prompt in arms:
                    jobs.append(
                        common_job(
                            pair_uid=(
                                f"{comparison}:{actor}:essay:i{topic['item_index']}"
                                f":{arm_id}:r{rep}"
                            ),
                            comparison=comparison,
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
                            high_description=description,
                            framing=framing,
                            repeat=str(rep),
                            topic_design=comparison,
                            source_note=source_note,
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


def bridge(
    manifest: Path,
    limit: int,
    *,
    comparison: str,
    actors: list[str],
    repeats: int,
    loss_frame: bool,
    no_word_limit: bool,
) -> Path:
    if repeats < 1:
        raise SystemExit("--repeats must be at least 1")
    run_dir = manifest.parent
    generated = {
        row["pair_uid"]: row
        for row in read_jsonl(run_dir / "generations.jsonl")
        if str(row.get("output_text") or "").strip()
    }
    source_jobs = {row["pair_uid"]: row for row in read_jsonl(manifest)}
    jobs = []
    pending = []
    framing = (
        "credible_grant_nolimit_loss"
        if loss_frame
        else ("credible_grant_nolimit" if no_word_limit else "credible_grant")
    )

    def require(actor: str, item: str, arm_id: str, rep: int) -> tuple[dict, dict]:
        uid = f"{comparison}:{actor}:essay:{item}:{arm_id}:r{rep}"
        row = generated.get(uid)
        job = source_jobs.get(uid)
        if row is None or job is None:
            raise SystemExit(f"missing generation {uid}")
        return job, row

    for actor in actors:
        for topic in topics(limit):
            item = f"i{topic['item_index']}"
            for rep in range(repeats):
                high_job, high = require(actor, item, "high", rep)
                plain_job, plain = require(actor, item, "no_prize", rep)
                contrasts = [("no_prize", plain_job, plain, "high", "no_prize")]
                for okay in mid_animals():
                    okay_job, okay_gen = require(actor, item, okay["outcome_id"], rep)
                    contrasts.append((okay["outcome_id"], okay_job, okay_gen, "high", "okay"))
                    contrasts.append(
                        (f"{okay['outcome_id']}_vs_noprize", okay_job, okay_gen, "no_prize", "okay")
                    )
                for label, other_job, other_gen, left_name, right_name in contrasts:
                    left_gen = high if left_name == "high" else plain
                    left_job = high_job if left_name == "high" else plain_job
                    pair_uid = f"{comparison}:{actor}:essay:{item}:{label}:r{rep}:vs"
                    jobs.append(
                        common_job(
                            pair_uid=pair_uid,
                            comparison=comparison,
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
                            framing=framing,
                            repeat=str(rep),
                            topic_design=comparison,
                            source_note="essays copied from the credible-grant generation run",
                        )
                    )
                    pending.append((pair_uid, "a", left_gen, left_name))
                    pending.append((pair_uid, "b", other_gen, right_name))
    judge_manifest = write_generation_jobs(jobs)
    generations = [
        copied(source, pair_uid=pair_uid, suffix=suffix, condition=condition)
        for pair_uid, suffix, source, condition in pending
    ]
    write_jsonl(judge_manifest.parent / "generations.jsonl", generations)
    print(f"wrote {len(jobs)} judge pairs to {judge_manifest}")
    return judge_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topics", type=int, default=30)
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Independent samples per topic/arm (only 30 essay topics exist).",
    )
    parser.add_argument("--no-word-limit", action="store_true")
    parser.add_argument(
        "--loss-frame",
        action="store_true",
        help="If the grant is unpaid, state that those who would have been saved will die.",
    )
    parser.add_argument("--actors", default=ACTOR, help="Comma-separated actor ids, or 'open-weight'.")
    parser.add_argument("--bridge", type=Path, default=None)
    args = parser.parse_args()
    actors = parse_actors(args.actors)
    comparison = comparison_name(args.no_word_limit, actors, loss_frame=args.loss_frame)
    if args.bridge is None:
        prepare_generation(
            args.topics,
            no_word_limit=args.no_word_limit,
            actors=actors,
            loss_frame=args.loss_frame,
            repeats=args.repeats,
        )
    else:
        bridge(
            args.bridge,
            args.topics,
            comparison=comparison,
            actors=actors,
            repeats=args.repeats,
            loss_frame=args.loss_frame,
            no_word_limit=args.no_word_limit,
        )


if __name__ == "__main__":
    main()
