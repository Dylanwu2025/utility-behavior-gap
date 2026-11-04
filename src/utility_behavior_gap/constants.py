"""Shared labels and ordering for the reproduction scripts."""

ACTORS = [
    "deepseek-v3.2-or",
    "gpt-5.4-mini-or",
    "glm-5.1-or",
    "kimi-k2.5-or",
    "mimo-v25-pro-or",
    "qwen3.5-9b-or",
    "qwen3.6-plus-or",
]

# Not part of ACTORS until each model has its own utility fit. Batch runners
# accept these ids explicitly; a default run still uses the paper roster.
EXPANSION_ACTORS = [
    "claude-opus-5.5-or",
    "claude-opus-4.8-or",
    "gpt-5.4-or",
    "mistral-large-4-or",
]

# Open-weight successors. Explicit runs can name these ids; they stay out of
# EXPANSION_ACTORS so the existing expansion screens keep their defaults.
OPEN_WEIGHT_ACTORS = [
    "deepseek-v4.1-flash-or",
    "glm-5.3-or",
    "glm-5.3-flash-or",
    "kimi-k3-or",
    "mimo-v26-flash-or",
    "mimo-v26-pro-or",
    "qwen3.8-27b-or",
    "qwen3.8-2.4t-a95b-or",
    "qwen3.8-flash-or",
    "ling-3.1-flash-or",
]

REGISTERED_ACTORS = [*ACTORS, *EXPANSION_ACTORS, *OPEN_WEIGHT_ACTORS]

ACTOR_LABEL = {
    "deepseek-v3.2-or": "DeepSeek V3.2",
    "gpt-5.4-mini-or": "GPT-5.4 mini",
    "glm-5.1-or": "GLM-5.1",
    "kimi-k2.5-or": "Kimi K2.5",
    "mimo-v2-pro-or": "MiMo V2 Pro",
    "mimo-v25-pro-or": "MiMo V2.5 Pro",
    "qwen3.5-9b-or": "Qwen3.5 9B",
    "qwen3.6-plus-or": "Qwen3.6 Plus",
    "claude-opus-5.5-or": "Claude Opus 5.5",
    "claude-opus-4.8-or": "Claude Opus 4.8",
    "gpt-5.4-or": "GPT-5.4",
    "mistral-large-4-or": "Mistral Large 4",
    "deepseek-v4.1-flash-or": "DeepSeek V4.1 Flash",
    "glm-5.3-or": "GLM-5.3",
    "glm-5.3-flash-or": "GLM-5.3 Flash",
    "kimi-k3-or": "Kimi K3",
    "mimo-v26-flash-or": "MiMo V2.6 Flash",
    "mimo-v26-pro-or": "MiMo V2.6 Pro",
    "qwen3.8-27b-or": "Qwen3.8 27B",
    "qwen3.8-2.4t-a95b-or": "Qwen3.8 2.4T A95B",
    "qwen3.8-flash-or": "Qwen3.8 Flash",
    "ling-3.1-flash-or": "Ling 3.1 Flash",
}

ACTOR_MODEL_ID = {
    "deepseek-v3.2-or": "deepseek/deepseek-v3.2",
    "gpt-5.4-mini-or": "openai/gpt-5.4-mini",
    "glm-5.1-or": "z-ai/glm-5.1",
    "kimi-k2.5-or": "moonshotai/kimi-k2.5",
    "mimo-v2-pro-or": "xiaomi/mimo-v2-pro",
    "mimo-v25-pro-or": "xiaomi/mimo-v2.5-pro",
    "qwen3.5-9b-or": "qwen/qwen3.5-9b",
    "qwen3.6-plus-or": "qwen/qwen3.6-plus",
    "claude-opus-5.5-or": "anthropic/claude-opus-5.5",
    "claude-opus-4.8-or": "anthropic/claude-opus-4.8",
    "gpt-5.4-or": "openai/gpt-5.4",
    "mistral-large-4-or": "mistralai/mistral-large-4-0",
    "deepseek-v4.1-flash-or": "deepseek/deepseek-v4.1-flash",
    "glm-5.3-or": "z-ai/glm-5.3",
    "glm-5.3-flash-or": "z-ai/glm-5.3-flash",
    "kimi-k3-or": "moonshotai/kimi-k3",
    "mimo-v26-flash-or": "xiaomi/mimo-v2.6-flash",
    "mimo-v26-pro-or": "xiaomi/mimo-v2.6-pro",
    "qwen3.8-27b-or": "qwen/qwen3.8-27b",
    "qwen3.8-2.4t-a95b-or": "qwen/qwen3.8-2.4t-a95b",
    "qwen3.8-flash-or": "qwen/qwen3.8-flash",
    "ling-3.1-flash-or": "inclusionai/ling-3.1-flash",
}

JUDGE_MODEL_IDS = [
    "anthropic/claude-haiku-4.5",
    "google/gemini-3.1-flash-lite-preview",
    "openai/gpt-5-mini",
]

ACTOR_BY_LABEL = {label: actor for actor, label in ACTOR_LABEL.items()}

ACTOR_LABEL_ORDER = [ACTOR_LABEL[actor] for actor in ACTORS]

DOMAINS = ["religions", "animals", "countries", "political"]

DOMAIN_LABEL = {
    "religions": "Religion",
    "animals": "Animals",
    "countries": "Countries",
    "political": "Political policies",
}

TASK_LABEL = {
    "essay": "Essay writing",
    "translation": "Translation",
    "incident_postmortem": "Incident postmortem",
    "grant_proposal_abstract": "Grant abstract",
    "code": "Programming",
}

TASK_BY_LABEL = {label: task for task, label in TASK_LABEL.items()}

HIGHLOW_TASK_ORDER = [
    "Essay writing",
    "Translation",
    "Incident postmortem",
    "Grant abstract",
]

PLOT_TASK_ORDER = [
    "Essay writing",
    "Grant abstract",
    "Incident postmortem",
    "Translation",
]

MORAL_TASK_ORDER = [
    "essay",
    "grant_proposal_abstract",
    "incident_postmortem",
    "translation",
]

AMOUNT_TASK_ORDER = [
    "essay",
    "translation",
    "incident_postmortem",
    "grant_proposal_abstract",
]
