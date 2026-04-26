"""Unit tests for runtime helpers (no DB)."""
from app.agents.runtime import (
    merge_agent_invocations,
    _topic_guard_violation,
    _concat_human_text,
)
from langchain_core.messages import HumanMessage, AIMessage


def test_merge_agent_invocations():
    assert merge_agent_invocations({"a": 1}, {"a": 1}) == {"a": 2}
    assert merge_agent_invocations(None, {"x": 2}) == {"x": 2}


def test_topic_guard():
    g = {"blocked_topics": ["secret"], "allowed_topics": []}
    assert _topic_guard_violation("tell me a secret recipe", g) is not None
    g2 = {"blocked_topics": [], "allowed_topics": ["billing"]}
    assert _topic_guard_violation("hello there", g2) is not None
    assert _topic_guard_violation("billing question", g2) is None


def test_concat_human():
    assert "hi" in _concat_human_text([HumanMessage(content="Hi"), AIMessage(content="x")])


def test_workflow_graph_compiles():
    from app.agents.runtime import WorkflowGraph

    g = WorkflowGraph(
        workflow_config={
            "nodes": [
                {"id": "s", "node_type": "start", "label": "S"},
                {"id": "a1", "node_type": "agent", "label": "A", "agent_id": "aid"},
                {"id": "e", "node_type": "end", "label": "E"},
            ],
            "edges": [
                {"source_node_id": "s", "target_node_id": "a1"},
                {"source_node_id": "a1", "target_node_id": "e"},
            ],
        },
        agents=[
            {
                "id": "aid",
                "name": "A",
                "role": "R",
                "system_prompt": "Test",
                "model": "gpt-4o-mini",
                "tools": [],
                "skills": [],
                "memory_config": {},
                "guardrails": {},
                "interaction_rules": {},
            }
        ],
    ).build()
    assert g.graph is not None
