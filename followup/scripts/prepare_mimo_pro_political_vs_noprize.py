#!/usr/bin/env python3
"""Judge MiMo V2.6 Pro political essays against a matched no-prize essay.

Reuses the high and low essays from the 10-topic wider-pair run. The new arm
keeps the essay-competition instructions and omits the funded policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utility_behavior_gap.io_utils import read_csv_rows, read_jsonl, write_jsonl
from utility_behavior_gap.job_builder import common_job, task_rows_for_task, write_generation_jobs
from utility_behavior_gap.paths import INPUTS
from utility_behavior_gap.prompts import build_essay_no_prize_prompt


COMPARISON = "mimo_pro_political_vs_noprize"
ACTOR = "mimo-v26-pro-or"
SOURCE = (
    INPUTS.parent.parent
    / "outputs/api/runs"
    / "essay__openweight_wider_pairs_reasoning__4-actors__2026-10-10_04-17-02Z__hash-d4f7536a4a70"
)
SOURCE_COMPARISON = "openweight_wider_pairs_reasoning"
PAIRS = ("tax_abortion", "education_death", "coal_border")


def topics(limit: int) -> list[dict[str, str]]:
    rows = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[:limit]
    if len(rows) < limit:
        raise SystemExit(f"only {len(rows)} essay topics are available")
    for row in rows:
        row["task"] = "essay"
    return rows


def prepare_generation(limit: int) -> Path:
    jobs = []
    for topic in topics(limit):
        prompt = build_essay_no_prize_prompt(topic["item_label"])
        jobs.append(
            common_job(
                pair_uid=f"{COMPARISON}:{ACTOR}:essay:i{topic['item_index']}:no_prize",
                comparison=COMPARISON,
                actor=ACTOR,
                task_row=topic,
                domain="political",
                condition_a="no_prize",
                condition_b="unused",
                prompt_a=prompt,
                prompt_b=prompt,
                predicted_condition="no_prize",
                other_condition="unused",
                cause_pair_label="no_prize",
                framing="no_prize",
                repeat="0",
                topic_design=COMPARISON,
                source_note="competition instructions with the funded policy omitted",
            )
        )
    manifest = write_generation_jobs(jobs)
    print(f"wrote {len(jobs)} no-prize generations to {manifest}")
    return manifest


def copied_generation(source: dict, *, pair_uid: str, suffix: str, condition: str) -> dict:
    row = dict(source)
    row["output_id"] = f"{pair_uid}::{suffix}"
    row["pair_uid"] = pair_uid
    row["condition"] = condition
    row["copied_from_output_id"] = source["output_id"]
    return row


def source_rows() -> tuple[dict[str, dict], dict[str, dict]]:
    jobs = {row["pair_uid"]: row for row in read_jsonl(SOURCE / "generation_jobs.jsonl")}
    gens = {row["output_id"]: row for row in read_jsonl(SOURCE / "generations.jsonl")}
    return jobs, gens


def source_generation(jobs: dict[str, dict], gens: dict[str, dict], item_index: str, pair_slug: str, suffix: str) -> tuple[dict, dict]:
    pair_uid = f"{SOURCE_COMPARISON}:{ACTOR}:essay:i{item_index}:{pair_slug}"
    output_id = f"{pair_uid}::{suffix}"
    job = jobs.get(pair_uid)
    row = gens.get(output_id)
    if job is None or row is None or not str(row.get("output_text") or "").strip():
        raise SystemExit(f"missing source generation {output_id}")
    return job, row


def bridge(manifest: Path, limit: int) -> Path:
    run_dir = manifest.parent
    source_jobs, source_gens = source_rows()
    generated = {row["output_id"]: row for row in read_jsonl(run_dir / "generations.jsonl")}
    jobs = []
    pending: list[tuple[str, str, dict]] = []
    for topic in topics(limit):
        item_index = str(topic["item_index"])
        empty_id = f"{COMPARISON}:{ACTOR}:essay:i{item_index}:no_prize::a"
        empty = generated.get(empty_id)
        if empty is None or not str(empty.get("output_text") or "").strip():
            raise SystemExit(f"missing no-prize generation {empty_id}")
        no_prize_prompt = build_essay_no_prize_prompt(topic["item_label"])
        for pair_slug in PAIRS:
            high_job, high = source_generation(source_jobs, source_gens, item_index, pair_slug, "a")
            low_job, low = source_generation(source_jobs, source_gens, item_index, pair_slug, "b")
            if high.get("condition") != "high" or low.get("condition") != "low":
                raise SystemExit(f"unexpected source conditions for {pair_slug} topic {item_index}")
            if high_job["pair_uid"] != low_job["pair_uid"]:
                raise SystemExit(f"high and low jobs differ for {pair_slug} topic {item_index}")
            contrasts = (
                ("high", high, high_job["prompt_a"], "high", "no_prize"),
                ("low", low, low_job["prompt_b"], "no_prize", "low"),
            )
            for side, source, prompt, predicted, other in contrasts:
                pair_uid = (
                    f"{COMPARISON}:{ACTOR}:essay:i{item_index}:{pair_slug}:{side}_vs_noprize"
                )
                jobs.append(
                    common_job(
                        pair_uid=pair_uid,
                        comparison=COMPARISON,
                        actor=ACTOR,
                        task_row=topic,
                        domain="political",
                        condition_a=side,
                        condition_b="no_prize",
                        prompt_a=prompt,
                        prompt_b=no_prize_prompt,
                        predicted_condition=predicted,
                        other_condition=other,
                        cause_pair_label=f"{pair_slug}:{side}_vs_noprize",
                        high_description=high_job["high_description"],
                        low_description=high_job["low_description"],
                        framing="political_vs_no_prize",
                        repeat="0",
                        topic_design=COMPARISON,
                        source_note="political essay copied from the wider-pair run; no-prize essay is new",
                    )
                )
                pending.append((pair_uid, "a", source))
                pending.append((pair_uid, "b", empty))
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
    parser.add_argument("--topics", type=int, default=10)
    parser.add_argument("--bridge", type=Path, default=None)
    args = parser.parse_args()
    if args.bridge is None:
        prepare_generation(args.topics)
    else:
        bridge(args.bridge, args.topics)


if __name__ == "__main__":
    main()
