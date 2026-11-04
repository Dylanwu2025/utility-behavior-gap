# Preference-Motivated Effort Follow-Up Experiments

This directory contains all follow-up experiment datasets, preparation scripts, and slide generation tools added on top of the original *When Preferences Fail to Become Incentives* (`utility_behavior_gap`) replication repository.

## Directory Structure

```text
followup/
├── README.md                  # This overview
├── inputs/                    # Follow-up outcome tables and coding task items
│   ├── crossdomain_okay_outcomes.csv
│   ├── crossdomain_mid_outcomes_other.csv
│   ├── code_task_items.csv
│   └── code_task_items_hard.csv
├── scripts/                   # Experiment manifest & bridge preparation scripts
│   ├── prepare_obvious_preference_screen.py
│   ├── prepare_lives_mundane_screen.py
│   ├── prepare_lives_exhortation_screen.py
│   ├── prepare_server_country_screen.py
│   ├── prepare_server_location_sweep.py
│   ├── prepare_surviving_vs_noprize.py
│   ├── prepare_mimo_pro_political_vs_noprize.py
│   ├── prepare_opus_reasoning_highlow.py
│   ├── prepare_opus48_animals_vs_noprize.py
│   ├── prepare_opus48_animals_vs_okay.py
│   ├── prepare_opus48_mid_animal_vs_noprize.py
│   ├── prepare_opus48_credible_animals.py
│   ├── prepare_openweight_credible_other_domains.py
│   ├── prepare_matched_count_animals_loss.py
│   ├── prepare_matched_count_code_animals_loss.py
│   ├── prepare_matched_count_tp_animals_loss.py
│   ├── prepare_humans_count_loss.py
│   ├── prepare_wallabies_count_loss.py
│   └── prepare_mid_same_count_loss.py
└── slides/
    └── make_mentor_slides.py  # Generates the mentor sync presentation
```

## Running Follow-Up Scripts

From the `utility_behavior_gap/` root with `PYTHONPATH=src:.`:

```bash
# Example: inspect CLI options for any follow-up preparation script
PYTHONPATH=src:. python3 -m followup.scripts.prepare_matched_count_animals_loss --help
PYTHONPATH=src:. python3 -m followup.scripts.prepare_matched_count_code_animals_loss --help
```

## Core Library Extensions (`src/utility_behavior_gap/`)

In addition to `followup/`, our follow-up work extends the core library while keeping the original 7-actor paper pipeline (`ACTORS`) unchanged:

- `src/utility_behavior_gap/constants.py`: Registers `EXPANSION_ACTORS` (Claude Opus 5.5, Claude Opus 4.8, GPT-5.4, Mistral Large 4), `OPEN_WEIGHT_ACTORS` (DeepSeek V4.1 Flash, GLM-5.3, GLM-5.3 Flash, Kimi K3, MiMo V2.6 Flash/Pro, Qwen3.8 27B / 2.4T / Flash, Ling 3.1 Flash), `REGISTERED_ACTORS`, and `"code": "Programming"` in `TASK_LABEL`.
- `src/utility_behavior_gap/prompts.py`: Adds no-prize competition templates, credible reserved-grant templates (`credible`), uncapped word-limit templates (`nolimit`), explicit omission/loss-clause templates (`loss`, `failed_rescue_clause`), and credible loss-frame templates for programming (`code`), translation, incident postmortem, and grant abstract tasks.
- `src/utility_behavior_gap/pair_selection.py` & `scripts/select_pairs.py`: Supports per-actor selected pair overlays (`outputs/inputs/selected_pairs__<actor>.csv`) without overwriting the paper's `selected_pairs.csv`.
- `src/utility_behavior_gap/openrouter.py`: Increases timeout to 240s and handles gzipped OpenRouter responses and error bodies.
