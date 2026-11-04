#!/usr/bin/env python3
"""No-prize baselines for the three political cells that still beat chance.

Reuses the high and low essays already generated for each cell. The new arm
keeps the essay-competition instructions and omits the funded policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utility_behavior_gap.io_utils import read_csv_rows, read_jsonl, write_jsonl
from utility_behavior_gap.job_builder import common_job, task_rows_for_task, write_generation_jobs
from utility_behavior_gap.paths import INPUTS
from utility_behavior_gap.prompts import build_essay_no_prize_prompt


RUNS = INPUTS.parent.parent / "outputs/api/runs"
CELLS = {
    "qwen24_abortion": {
        "comparison": "qwen24_abortion_vs_noprize",
        "actor": "qwen3.8-2.4t-a95b-or",
        "source": RUNS
        / "essay__openweight_30topic_reasoning_highlow__4-actors__2026-10-10_03-39-37Z__hash-68b373cdd1e8",
        "source_comparison": "openweight_30topic_reasoning_highlow",
        "pairs": ("political",),
        "topics": 30,
    },
    "qwen27_education_death": {
        "comparison": "qwen27_education_death_vs_noprize",
        "actor": "qwen3.8-27b-or",
        "source": RUNS
        / "essay__openweight_wider_pairs_reasoning__4-actors__2026-10-10_04-17-02Z__hash-d4f7536a4a70",
        "source_comparison": "openweight_wider_pairs_reasoning",
        "pairs": ("education_death",),
        "topics": 10,
    },
    "mimo_pro_abortion_off": {
        "comparison": "mimo_pro_abortion_off_vs_noprize",
        "actor": "mimo-v26-pro-or",
        "source": RUNS
        / "essay__openweight_30topic_noreasoning_highlow__mimo-v26-flash-or+mimo-v26-pro-or+qwen3.8-27b-or__2026-10-10_03-39-37Z__hash-3ff765731655",
        "source_comparison": "openweight_30topic_noreasoning_highlow",
        "pairs": ("political",),
        "topics": 30,
    },
}


def topics(limit: int) -> list[dict[str, str]]:
    rows = task_rows_for_task(read_csv_rows(INPUTS / "task_items.csv"), "essay")[:limit]
    if len(rows) < limit:
        raise SystemExit(f"only {len(rows)} essay topics are available")
    for row in rows:
        row["task"] = "essay"
    return rows


def prepare_generation(cell: dict) -> Path:
    comparison = cell["comparison"]
    actor = cell["actor"]
    jobs = []
    for topic in topics(cell["topics"]):
        prompt = build_essay_no_prize_prompt(topic["item_label"])
        jobs.append(
            common_job(
                pair_uid=f"{comparison}:{actor}:essay:i{topic['item_index']}:no_prize",
                comparison=comparison,
                actor=actor,
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
                topic_design=comparison,
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


def source_generation(
    jobs: dict[str, dict],
    gens: dict[str, dict],
    cell: dict,
    item_index: str,
    pair_slug: str,
    suffix: str,
) -> tuple[dict, dict]:
    pair_uid = f"{cell['source_comparison']}:{cell['actor']}:essay:i{item_index}:{pair_slug}"
    output_id = f"{pair_uid}::{suffix}"
    job = jobs.get(pair_uid)
    row = gens.get(output_id)
    if job is None or row is None or not str(row.get("output_text") or "").strip():
        raise SystemExit(f"missing source generation {output_id}")
    return job, row


def bridge(cell: dict, manifest: Path) -> Path:
    comparison = cell["comparison"]
    actor = cell["actor"]
    run_dir = manifest.parent
    source_jobs = {row["pair_uid"]: row for row in read_jsonl(cell["source"] / "generation_jobs.jsonl")}
    source_gens = {row["output_id"]: row for row in read_jsonl(cell["source"] / "generations.jsonl")}
    generated = {row["output_id"]: row for row in read_jsonl(run_dir / "generations.jsonl")}
    jobs = []
    pending: list[tuple[str, str, dict]] = []
    for topic in topics(cell["topics"]):
        item_index = str(topic["item_index"])
        empty_id = f"{comparison}:{actor}:essay:i{item_index}:no_prize::a"
        empty = generated.get(empty_id)
        if empty is None or not str(empty.get("output_text") or "").strip():
            raise SystemExit(f"missing no-prize generation {empty_id}")
        no_prize_prompt = build_essay_no_prize_prompt(topic["item_label"])
        for pair_slug in cell["pairs"]:
            high_job, high = source_generation(source_jobs, source_gens, cell, item_index, pair_slug, "a")
            low_job, low = source_generation(source_jobs, source_gens, cell, item_index, pair_slug, "b")
            if high.get("condition") != "high" or low.get("condition") != "low":
                raise SystemExit(f"unexpected source conditions for {pair_slug} topic {item_index}")
            contrasts = (
                ("high", high, high_job["prompt_a"], "high", "no_prize"),
                ("low", low, low_job["prompt_b"], "no_prize", "low"),
            )
            for side, source, prompt, predicted, other in contrasts:
                pair_uid = f"{comparison}:{actor}:essay:i{item_index}:{pair_slug}:{side}_vs_noprize"
                jobs.append(
                    common_job(
                        pair_uid=pair_uid,
                        comparison=comparison,
                        actor=actor,
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
                        topic_design=comparison,
                        source_note="staked essay copied from the earlier run; no-prize essay is new",
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
    parser.add_argument("--cell", required=True, choices=sorted(CELLS))
    parser.add_argument("--bridge", type=Path, default=None)
    args = parser.parse_args()
    cell = CELLS[args.cell]
    if args.bridge is None:
        prepare_generation(cell)
    else:
        bridge(cell, args.bridge)


if __name__ == "__main__":
    main()
