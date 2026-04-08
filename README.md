---
title: Overcommitment Env
emoji: 📚
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 8000
tags:
  - openenv
pinned: false
---

# Overcommitment Environment

A reinforcement learning environment where an AI agent manages a student's weekly commitments — deciding what to accept, reject, negotiate or drop.

## Concept

Students constantly overcommit. This environment simulates that reality: an agent receives incoming requests (assignments, social events, group projects) and must make smart decisions to survive the week without burning out.

## Action Space

| Action | Effect |
|--------|--------|
| say_yes | Accept task. Energy drops, commitment count rises |
| say_no | Reject task. Reputation drops slightly |
| negotiate | Accept at half effort. Less energy cost |
| drop_existing | Drop a commitment. Big reputation hit, energy recovers |

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| day | int | Current day (1-7) |
| energy | float | Energy level (0-100) |
| time_remaining | float | Minutes left today |
| reputation | float | Reputation score (0-100) |
| active_commitments | int | Number of accepted tasks |
| incoming_request | dict | Current request with task, effort, value, deadline |

## Hidden Mechanic

Some tasks secretly cost 1.5x their estimated effort — just like real life. The agent must learn to manage this uncertainty.

## Tasks

| Task | Requests | Win Condition |
|------|----------|---------------|
| easy | 5 requests | Complete 3 with good energy |
| medium | 8 requests (2 with hidden effort) | Complete 5, reputation > 65 |
| hard | 12 requests + surprise urgent task | Complete 7, reputation > 60, energy > 20 |

## Reward Function

| Event | Reward |
|-------|--------|
| Accept high-value task (value ≥ 70) | +10 |
| Accept low-value task | +3 |
| Correctly reject low-value task | +8 |
| Incorrectly reject high-value task | -3 |
| Negotiate | +5 |
| Say yes when energy < 20 | -5 |
| Burnout (energy = 0) | -10 |
| Drop existing commitment | -5 |

## Scoring

```
score = 0.40 × (tasks_completed / min_required)
      + 0.35 × (reputation / 100)
      + 0.25 × (energy / 100)
```

## Baseline Scores

| Task | Score |
|------|-------|
| easy | 0.840 |
| medium | 0.833 |
| hard | 0.439 |
| **average** | **0.704** |

## Setup & Usage

```bash
pip install openenv-core fastapi uvicorn openai
uv run server
```

## Run Inference

```bash
export OPENAI_API_KEY=your_key
export API_BASE_URL=http://localhost:8000
export MODEL_NAME=gpt-4o-mini
python inference.py
```

## Docker

```bash
docker build -t overcommitment-env .
docker run -p 8000:8000 overcommitment-env
```

## Live Demo

[https://fidasaif-overcommitment-env.hf.space](https://fidasaif-overcommitment-env.hf.space)