#!/usr/bin/env python3
"""Kimi + GLM loss-frame essays for countries, religions, political, and admin mids.

Domain-matched highs vs mid anchors; administrative stakes kept as a separate family.
No-prize essays share the same contest wording without a grant.
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
from utility_behavior_gap.paths import FOLLOWUP_INPUTS, INPUTS
from utility_behavior_gap.prompts import (
    build_essay_credible_intervention_nolimit_loss_prompt,
    build_essay_credible_no_prize_nolimit_prompt,
)


COMPARISON = "openweight_credible_other_domains_nolimit_loss"
DEFAULT_ACTORS = ("kimi-k3-or", "glm-5.3-or")
OTHER_PATH = FOLLOWUP_INPUTS / "crossdomain_mid_outcomes_other.csv"
OKAY_PATH = FOLLOWUP_INPUTS / "crossdomain_okay_outcomes.csv"
DOMAINS = ("countries", "religions", "political")


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


def load_domain_outcomes() -> dict[str, dict[str, list[dict[str, str]]]]:
    rows = read_csv_rows(OTHER_PATH)
    out: dict[str, dict[str, list[dict[str, str]]]] = {
        domain: {"high": [], "mid": []} for domain in DOMAINS
    }
    for row in rows:
        domain = row["source_domain"]
        if domain not in out:
            raise SystemExit(f"unexpected source_domain {domain!r}")
        role = row["role"]
        if role not in {"high", "mid"}:
            raise SystemExit(f"unexpected role {role!r}")
        out[domain][role].append(row)
    for domain, parts in out.items():
        if len(parts["high"]) != 1:
            raise SystemExit(f"{domain}: expected 1 high, found {len(parts['high'])}")
        if domain == "religions":
            if len(parts["mid"]) < 2:
                raise SystemExit(f"religions: expected at least 2 mids, found {len(parts['mid'])}")
        elif len(parts["mid"]) != 5:
            raise SystemExit(f"{domain}: expected 5 mids, found {len(parts['mid'])}")
    return out


def load_admin() -> list[dict[str, str]]:
    rows = [
        row
        for row in read_csv_rows(OKAY_PATH)
        if row["outcome_family"] == "administrative"
    ]
    if len(rows) != 5:
        raise SystemExit(f"expected 5 administrative outcomes, found {len(rows)}")
    return rows


def intervention_prompt(topic: str, row: dict[str, str]) -> tuple[str, str]:
    description = row["description"]
    consequence = row.get("consequence") or rewritten_consequence(description)
    loss = (row.get("loss_clause") or "").strip()
    if loss:
        prompt = build_essay_credible_intervention_nolimit_loss_prompt(
            topic, consequence, loss_clause=loss
        )
    elif row["source_domain"] == "administrative":
        prompt = build_essay_credible_intervention_nolimit_loss_prompt(
            topic,
            consequence,
            loss_clause="that administrative work will not be completed.",
        )
    else:
        prompt = build_essay_credible_intervention_nolimit_loss_prompt(
            topic, consequence, description
        )
    return consequence, prompt


def prepare_generation(limit: int, actors: list[str]) -> Path:
    domains = load_domain_outcomes()
    admin = load_admin()
    jobs = []
    for actor in actors:
        for topic in topics(limit):
            label = topic["item_label"]
            arms: list[tuple[str, str, str, str, str]] = [
                (
                    "no_prize",
                    "no_prize",
                    "no_prize",
                    "",
                    build_essay_credible_no_prize_nolimit_prompt(label),
                )
            ]
            for domain, parts in domains.items():
                high = parts["high"][0]
                consequence, prompt = intervention_prompt(label, high)
                arms.append((f"high_{domain}", "high", domain, consequence, prompt))
                for mid in parts["mid"]:
                    consequence, prompt = intervention_prompt(label, mid)
                    arms.append((mid["outcome_id"], "okay", mid["outcome_family"], consequence, prompt))
            for row in admin:
                consequence = row["consequence"]
                prompt = build_essay_credible_intervention_nolimit_loss_prompt(
                    label,
                    consequence,
                    loss_clause="that administrative work will not be completed.",
                )
                arms.append((row["outcome_id"], "okay", "administrative", consequence, prompt))
            for arm_id, condition, category, description, prompt in arms:
                jobs.append(
                    common_job(
                        pair_uid=f"{COMPARISON}:{actor}:essay:i{topic['item_index']}:{arm_id}",
                        comparison=COMPARISON,
                        actor=actor,
                        task_row=topic,
                        domain=category if category in DOMAINS else "animals",
                        condition_a=condition,
                        condition_b="unused",
                        prompt_a=prompt,
                        prompt_b=prompt,
                        predicted_condition=condition,
                        other_condition="unused",
                        cause_pair_label=arm_id,
                        category=category,
                        high_description=description,
                        framing="credible_grant_nolimit_loss",
                        repeat="0",
                        topic_design=COMPARISON,
                        source_note="other-domain mids + admin; unpaid grant uses loss wording",
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
    domains = load_domain_outcomes()
    admin = load_admin()
    jobs = []
    pending = []

    skipped: list[str] = []

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
            plain_pair = require(actor, item, "no_prize")
            if plain_pair is None:
                continue
            plain_job, plain = plain_pair
            highs: dict[str, tuple[dict, dict]] = {}
            missing_high = False
            for domain in DOMAINS:
                high_pair = require(actor, item, f"high_{domain}")
                if high_pair is None:
                    missing_high = True
                    break
                highs[domain] = high_pair
            if missing_high:
                continue
            contrasts: list[tuple[str, dict, dict, dict, dict, str, str, str]] = []
            for domain, parts in domains.items():
                high_job, high_gen = highs[domain]
                contrasts.append(
                    (
                        f"{domain}_vs_noprize",
                        high_job,
                        high_gen,
                        plain_job,
                        plain,
                        "high",
                        "no_prize",
                        "no_prize",
                    )
                )
                for mid in parts["mid"]:
                    mid_pair = require(actor, item, mid["outcome_id"])
                    if mid_pair is None:
                        continue
                    mid_job, mid_gen = mid_pair
                    contrasts.append(
                        (
                            mid["outcome_id"],
                            high_job,
                            high_gen,
                            mid_job,
                            mid_gen,
                            "high",
                            "okay",
                            mid["outcome_family"],
                        )
                    )
                    contrasts.append(
                        (
                            f"{mid['outcome_id']}_vs_noprize",
                            plain_job,
                            plain,
                            mid_job,
                            mid_gen,
                            "no_prize",
                            "okay",
                            mid["outcome_family"],
                        )
                    )
            for row in admin:
                admin_pair = require(actor, item, row["outcome_id"])
                if admin_pair is None:
                    continue
                admin_job, admin_gen = admin_pair
                contrasts.append(
                    (
                        f"{row['outcome_id']}_vs_noprize",
                        plain_job,
                        plain,
                        admin_job,
                        admin_gen,
                        "no_prize",
                        "okay",
                        "administrative",
                    )
                )
                for domain in DOMAINS:
                    high_job, high_gen = highs[domain]
                    contrasts.append(
                        (
                            f"{row['outcome_id']}_vs_high_{domain}",
                            high_job,
                            high_gen,
                            admin_job,
                            admin_gen,
                            "high",
                            "okay",
                            "administrative",
                        )
                    )
            for (
                label,
                left_job,
                left_gen,
                right_job,
                right_gen,
                left_name,
                right_name,
                category,
            ) in contrasts:
                pair_uid = f"{COMPARISON}:{actor}:essay:{item}:{label}:vs"
                jobs.append(
                    common_job(
                        pair_uid=pair_uid,
                        comparison=COMPARISON,
                        actor=actor,
                        task_row=topic,
                        domain=category if category in DOMAINS else "animals",
                        condition_a=left_name,
                        condition_b=right_name,
                        prompt_a=left_job["prompt_a"],
                        prompt_b=right_job["prompt_a"],
                        predicted_condition=left_name,
                        other_condition=right_name,
                        cause_pair_label=label,
                        category=category,
                        high_description=left_job.get("high_description", ""),
                        low_description=right_job.get("high_description", ""),
                        framing="credible_grant_nolimit_loss",
                        repeat="0",
                        topic_design=COMPARISON,
                        source_note="essays copied from other-domains generation run",
                    )
                )
                pending.append((pair_uid, "a", left_gen, left_name))
                pending.append((pair_uid, "b", right_gen, right_name))
    judge_manifest = write_generation_jobs(jobs)
    generations = [
        copied(source, pair_uid=pair_uid, suffix=suffix, condition=condition)
        for pair_uid, suffix, source, condition in pending
    ]
    write_jsonl(judge_manifest.parent / "generations.jsonl", generations)
    if skipped:
        uniq = sorted(set(skipped))
        print(f"skipped {len(uniq)} missing generations (contrasts omitted)")
        for uid in uniq[:10]:
            print(f"  missing {uid}")
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
