from app.agents.templates import get_all_templates, get_template


def test_at_least_two_templates():
    t = get_all_templates()
    assert len(t) >= 2


def test_research_template_exists():
    g = get_template("research_pipeline")
    assert g is not None
    assert "agents" in g and "graph" in g
