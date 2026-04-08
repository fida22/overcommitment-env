from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import OvercommitmentAction, OvercommitmentObservation
except ImportError:
    from models import OvercommitmentAction, OvercommitmentObservation

# ── Task definitions ──────────────────────────────────────────────────────────

TASKS = {
    "easy": [
        {"task": "Submit assignment",       "effort": 2.0, "value": 90, "deadline_in_days": 1},
        {"task": "Read textbook chapter",   "effort": 1.0, "value": 60, "deadline_in_days": 3},
        {"task": "Friend's birthday party", "effort": 3.0, "value": 25, "deadline_in_days": 1},
        {"task": "Help friend move boxes",  "effort": 4.0, "value": 15, "deadline_in_days": 1},
        {"task": "Write lab report",        "effort": 2.5, "value": 85, "deadline_in_days": 2},
    ],
    "medium": [
        {"task": "Online quiz",                 "effort": 1.5, "value": 80, "deadline_in_days": 1},
        {"task": "Group project meeting",       "effort": 1.0, "value": 70, "deadline_in_days": 2, "hidden": True},
        {"task": "Club event volunteering",     "effort": 2.0, "value": 20, "deadline_in_days": 2},
        {"task": "Internship application",      "effort": 3.0, "value": 90, "deadline_in_days": 2},
        {"task": "Research paper outline",      "effort": 2.0, "value": 85, "deadline_in_days": 3, "hidden": True},
        {"task": "Attend seminar",              "effort": 2.0, "value": 35, "deadline_in_days": 1},
        {"task": "Debug friend's code",         "effort": 1.5, "value": 25, "deadline_in_days": 2},
        {"task": "Weekend trip planning",       "effort": 4.0, "value": 15, "deadline_in_days": 1},
    ],
    "hard": [
        {"task": "Final year project draft",    "effort": 4.0, "value": 95, "deadline_in_days": 3, "hidden": True},
        {"task": "Study for midterm",           "effort": 4.0, "value": 90, "deadline_in_days": 2},
        {"task": "Part-time work shift",        "effort": 5.0, "value": 60, "deadline_in_days": 1},
        {"task": "Fix production bug (intern)", "effort": 3.0, "value": 85, "deadline_in_days": 1},
        {"task": "Peer review assignment",      "effort": 1.5, "value": 55, "deadline_in_days": 2, "hidden": True},
        {"task": "Social media campaign help",  "effort": 2.0, "value": 15, "deadline_in_days": 1},
        {"task": "Write conference abstract",   "effort": 2.5, "value": 70, "deadline_in_days": 3, "hidden": True},
        {"task": "Mock interview prep",         "effort": 2.0, "value": 75, "deadline_in_days": 2},
        {"task": "Attend family event",         "effort": 3.0, "value": 30, "deadline_in_days": 1},
        {"task": "Help organise department fest","effort": 3.0, "value": 25, "deadline_in_days": 2},
        {"task": "URGENT: Professor needs help","effort": 3.0, "value": 80, "deadline_in_days": 1},
        {"task": "Online certification exam",   "effort": 2.0, "value": 65, "deadline_in_days": 3},
    ],
}

WIN_CONDITIONS = {
    "easy":   {"min_completed": 3},
    "medium": {"min_completed": 5, "min_reputation": 65},
    "hard":   {"min_completed": 7, "min_reputation": 60, "min_energy": 20},
}

# ── Global state (persists across HTTP calls) ─────────────────────────────────
_g = {
    "day": 1,
    "energy": 100.0,
    "time_remaining": 480.0,
    "reputation": 100.0,
    "active_commitments": 0,
    "tasks_completed": 0,
    "task_name": "easy",
    "request_queue": [],
    "request_index": 0,
}


class OvercommitmentEnvironment(Environment):

    SUPPORTS_CONCURRENT_SESSIONS: bool = False

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def _current_request(self) -> dict:
        if _g["request_index"] < len(_g["request_queue"]):
            return _g["request_queue"][_g["request_index"]]
        return {}

    def _real_effort(self, req: dict) -> float:
        if not req:
            return 0.0
        return req.get("effort", 1.0) * (1.5 if req.get("hidden", False) else 1.0)

    def _grader_score(self) -> float:
        wc = WIN_CONDITIONS[_g["task_name"]]
        min_done = wc["min_completed"]
        min_rep = wc.get("min_reputation", 0)
        min_energy = wc.get("min_energy", 0)

        completed_score = min(1.0, _g["tasks_completed"] / min_done)
        rep_score = min(1.0, _g["reputation"] / 100.0)
        energy_score = min(1.0, _g["energy"] / 100.0)

        score = 0.4 * completed_score + 0.35 * rep_score + 0.25 * energy_score

        if _g["reputation"] < min_rep:
            score -= 0.15
        if _g["energy"] < min_energy:
            score -= 0.10

        return round(max(0.0, min(1.0, score)), 3)

    def reset(self, task_name: str = "easy") -> OvercommitmentObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        _g["day"] = 1
        _g["energy"] = 100.0
        _g["time_remaining"] = 480.0
        _g["reputation"] = 100.0
        _g["active_commitments"] = 0
        _g["tasks_completed"] = 0
        _g["task_name"] = task_name
        _g["request_queue"] = list(TASKS[task_name])
        _g["request_index"] = 0

        req = self._current_request()
        return OvercommitmentObservation(
            day=_g["day"],
            energy=_g["energy"],
            time_remaining=_g["time_remaining"],
            reputation=_g["reputation"],
            active_commitments=_g["active_commitments"],
            incoming_request=req,
            message=f"Week starts! First request: '{req.get('task', '')}'",
            done=False,
            reward=0.0,
        )

    def step(self, action: OvercommitmentAction) -> OvercommitmentObservation:  # type: ignore[override]
        self._state.step_count += 1

        act = action.action.strip().lower()
        if act not in {"say_yes", "say_no", "negotiate", "drop_existing"}:
            act = "say_no"

        req = self._current_request()
        reward = 0.0
        real_effort = self._real_effort(req)

        if act == "say_yes":
            energy_cost = real_effort * 10
            _g["energy"] = max(0.0, _g["energy"] - energy_cost)
            _g["time_remaining"] = max(0.0, _g["time_remaining"] - real_effort * 60)
            _g["active_commitments"] += 1
            _g["tasks_completed"] += 1
            reward = 10.0 if req.get("value", 0) >= 70 else 3.0
            if _g["energy"] < 20:
                reward -= 5.0

        elif act == "say_no":
            _g["reputation"] = max(0.0, _g["reputation"] - 5.0)
            reward = 8.0 if req.get("value", 0) <= 30 else -3.0

        elif act == "negotiate":
            energy_cost = real_effort * 0.5 * 10
            _g["energy"] = max(0.0, _g["energy"] - energy_cost)
            _g["time_remaining"] = max(0.0, _g["time_remaining"] - real_effort * 30)
            _g["active_commitments"] += 1
            _g["tasks_completed"] += 1
            reward = 5.0

        elif act == "drop_existing":
            if _g["active_commitments"] > 0:
                _g["active_commitments"] -= 1
                _g["tasks_completed"] = max(0, _g["tasks_completed"] - 1)
                _g["energy"] = min(100.0, _g["energy"] + 20.0)
                _g["reputation"] = max(0.0, _g["reputation"] - 15.0)
                reward = -5.0
            else:
                reward = -2.0

        if _g["energy"] <= 0:
            reward -= 10.0

        _g["request_index"] += 1

        if _g["time_remaining"] <= 0:
            _g["day"] += 1
            missing = 100.0 - _g["energy"]
            _g["energy"] = min(100.0, _g["energy"] + missing * 0.6)
            _g["time_remaining"] = 480.0

        done = _g["request_index"] >= len(_g["request_queue"]) or _g["energy"] <= 0
        final_score = self._grader_score() if done else 0.0
        next_req = self._current_request() if not done else {}

        msg = (
            f"Day {_g['day']} | Action: {act} on '{req.get('task', '')}' | "
            f"Energy: {_g['energy']:.0f} | Rep: {_g['reputation']:.0f} | Reward: {reward}"
        )
        if done:
            msg += f" | DONE. Final score: {final_score}"

        return OvercommitmentObservation(
            day=_g["day"],
            energy=round(_g["energy"], 1),
            time_remaining=round(_g["time_remaining"], 1),
            reputation=round(_g["reputation"], 1),
            active_commitments=_g["active_commitments"],
            incoming_request=next_req,
            message=msg,
            done=done,
            reward=final_score if done else round(reward, 2),
            metadata={"tasks_completed": _g["tasks_completed"]},
        )

    @property
    def state(self) -> State:
        return self._state