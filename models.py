from openenv.core.env_server.types import Action, Observation
from pydantic import Field

class OvercommitmentAction(Action):
    """What the agent decides to do with the incoming request."""
    action: str = Field(
        ...,
        description="One of: say_yes, say_no, negotiate, drop_existing"
    )

class OvercommitmentObservation(Observation):
    """What the agent sees after each step."""
    day: int = Field(default=1)
    energy: float = Field(default=100.0)
    time_remaining: float = Field(default=480.0)
    reputation: float = Field(default=100.0)
    active_commitments: int = Field(default=0)
    incoming_request: dict = Field(default_factory=dict)
    message: str = Field(default="")