import os
import requests
from typing import List, Optional
from openai import OpenAI

# LLM proxy — injected by judges
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "llama-3.3-70b-versatile")
API_KEY      = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN", "")

# Your environment server — separate from LLM proxy
ENV_URL = "https://fidasaif-overcommitment-env.hf.space"

# OpenAI client uses judge's LLM proxy
client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
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

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def get_agent_action(obs: dict) -> str:
    req = obs.get("incoming_request", {})
    obs_text = f"""
Day: {obs.get('day')}
Energy: {obs.get('energy')}
Reputation: {obs.get('reputation')}
Time remaining: {obs.get('time_remaining')}
Active commitments: {obs.get('active_commitments')}
Incoming request: {req.get('task', 'none')} | effort: {req.get('effort', '?')} hrs | value: {req.get('value', '?')} | due in: {req.get('deadline_in_days', '?')} days
"""
    try:
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
    except Exception as e:
        print(f"[DEBUG] Model error: {e}", flush=True)
        return "say_no"

def run_task(task_name: str) -> float:
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env="overcommitment_env", model=MODEL_NAME)

    try:
        # Environment calls use ENV_URL (your HF Space)
        res = requests.post(f"{ENV_URL}/reset", json={"task_name": task_name})
        data = res.json()
        obs = data["observation"]
        done = data["done"]

        step = 0
        while not done:
            step += 1
            # LLM call uses API_BASE_URL via OpenAI client
            action = get_agent_action(obs)

            # Environment call uses ENV_URL
            res = requests.post(f"{ENV_URL}/step", json={"action": {"action": action}})
            data = res.json()
            obs = data["observation"]
            done = data["done"]
            reward = float(data["reward"])
            error = None

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action, reward=reward, done=done, error=error)

            if done:
                score = reward
                break

        success = score >= 0.5

    except Exception as e:
        print(f"[DEBUG] Exception: {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score

def main():
    for task in ["easy", "medium", "hard"]:
        run_task(task)

if __name__ == "__main__":
    main()