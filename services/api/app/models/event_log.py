from sqlmodel import SQLModel, Field
from typing import Optional


class EventLog(SQLModel, table=True):
    __tablename__ = "event_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    event_type: str = Field(index=True)
    actor_type: str = Field(default="agent")
    correlation_id: str = Field(index=True, default="")
    causation_id: str = Field(default="")
    payload_json: str = "{}"
    created_at: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "event_type": self.event_type,
            "actor_type": self.actor_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": json.loads(self.payload_json),
            "created_at": self.created_at,
        }
