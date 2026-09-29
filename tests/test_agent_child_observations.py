from __future__ import annotations

from contextlib import contextmanager

from app import agent as agent_module


class GenerationRecordingClient:
    def __init__(self) -> None:
        self.span_updates: list[dict] = []
        self.generation_updates: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        raise RuntimeError("offline")

    def get_current_trace_id(self) -> str:
        return "0" * 32

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)

    def update_current_generation(self, **kwargs) -> None:
        self.generation_updates.append(kwargs)


def test_generation_receives_model_usage_cost_and_scrubbed_prompt(monkeypatch) -> None:
    client = GenerationRecordingClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)

    @contextmanager
    def no_propagation(**kwargs):
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", no_propagation)

    agent = agent_module.LabAgent()
    result = agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="refund for student@vinuni.edu.vn",
        correlation_id="req-12345678",
    )

    retrieval_update = client.span_updates[0]
    assert retrieval_update["output"] == {"doc_count": 1}
    assert "student@" not in str(retrieval_update)

    generation = client.generation_updates[-1]
    assert generation["model"] == agent.model
    assert generation["usage_details"] == {
        "input": result.tokens_in,
        "output": result.tokens_out,
    }
    assert round(sum(generation["cost_details"].values()), 6) == result.cost_usd
    assert "student@" not in generation["input"]
    assert "[REDACTED_EMAIL]" in generation["input"]
    assert generation["prompt"] is None  # local fallback không có managed prompt
