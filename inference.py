import os
import requests
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")

client = OpenAI(
    api_key=OPENAI_KEY,
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """You are a student managing your weekly commitments.
Each step you receive a new request and must respond with exactly one of:
say_yes, say_no, negotiate, drop_existing

Rules:
- say_yes if the task is high value (value >= 70) and you have energy > 30
- say_no if the task is low value (value <= 30) or you have energy < 20
- negotiate if the task is medium value or you are low on energy
- drop_existing only if energy is critically low (< 10)

Reply with ONLY the action word, nothing else."""

def get_agent_action(observation: dict) -> str:
    req = observation.get("incoming_request", {})
    obs_text = f"""
Day: {observation.get('day')}
Energy: {observation.get('energy')}
Reputation: {observation.get('reputation')}
Time remaining: {observation.get('time_remaining')}
Active commitments: {observation.get('active_commitments')}
Incoming request: {req.get('task', 'none')} | effort: {req.get('effort', '?')} hrs | value: {req.get('value', '?')} | due in: {req.get('deadline_in_days', '?')} days
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": obs_text},
        ],
        max_tokens=10,
        temperature=0.0,
    )
    action = response.choices[0].message.content.strip().lower()
    valid = {"say_yes", "say_no", "negotiate", "drop_existing"}
    return action if action in valid else "say_no"

def run_task(task_name: str) -> float:
    print(f"\n{'='*50}")
    print(f"[START] Task: {task_name}")
    print(f"{'='*50}")

    # Reset
    res = requests.post(f"{API_BASE_URL}/reset", json={"task_name": task_name})
    obs = res.json()["observation"]
    done = res.json()["done"]
    step = 0

    while not done:
        step += 1
        action = get_agent_action(obs)
        print(f"[STEP {step}] Request: '{obs.get('incoming_request', {}).get('task', '')}' → Action: {action}")

        res = requests.post(f"{API_BASE_URL}/step", json={"action": {"action": action}})
        data = res.json()
        obs = data["observation"]
        done = data["done"]
        reward = data["reward"]

        print(f"         Energy: {obs['energy']} | Rep: {obs['reputation']} | Reward: {reward}")

    final_score = reward
    print(f"\n[END] Task: {task_name} | Final Score: {final_score}")
    return final_score

def main():
    scores = {}
    for task in ["easy", "medium", "hard"]:
        scores[task] = run_task(task)

    print(f"\n{'='*50}")
    print("FINAL SCORES")
    print(f"{'='*50}")
    for task, score in scores.items():
        print(f"  {task:10s}: {score:.3f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  {'average':10s}: {avg:.3f}")

if __name__ == "__main__":
    main()