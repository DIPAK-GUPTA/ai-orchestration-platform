"""
Pre-built Workflow Templates
----------------------------
Templates that users can instantiate in one click.
Each template defines agents + a graph definition.
"""

from typing import Any


TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "research_pipeline",
        "name": "Research & Report Pipeline",
        "description": "Researcher agent gathers info, Analyst summarizes, Writer produces final report. Classic 3-agent pipeline.",
        "category": "research",
        "icon": "search",
        "agents": [
            {
                "slot": "researcher",
                "name": "Researcher",
                "role": "Expert online researcher",
                "system_prompt": (
                    "You are an expert researcher. Your job is to gather comprehensive "
                    "information on any given topic. Use web search tools to find current, "
                    "accurate information. Organize your findings clearly with sources."
                ),
                "model": "gpt-4o-mini",
                "tools": ["web_search", "http_get", "get_datetime"],
            },
            {
                "slot": "analyst",
                "name": "Analyst",
                "role": "Data and content analyst",
                "system_prompt": (
                    "You are a skilled analyst. Take the raw research provided and "
                    "extract key insights, identify patterns, and produce a structured "
                    "analysis with bullet points, key findings, and recommendations."
                ),
                "model": "gpt-4o-mini",
                "tools": ["calculator", "json_parse"],
            },
            {
                "slot": "writer",
                "name": "Writer",
                "role": "Professional content writer",
                "system_prompt": (
                    "You are a professional writer. Take the analysis and produce a "
                    "polished, well-structured report with an executive summary, "
                    "detailed sections, and conclusions. Write for a business audience."
                ),
                "model": "gpt-4o-mini",
                "tools": ["text_summary"],
            },
        ],
        "graph": {
            "nodes": [
                {"id": "start", "node_type": "start", "label": "Start"},
                {"id": "n_researcher", "node_type": "agent", "label": "Research", "agent_slot": "researcher", "position": {"x": 100, "y": 200}},
                {"id": "n_analyst", "node_type": "agent", "label": "Analyze", "agent_slot": "analyst", "position": {"x": 350, "y": 200}},
                {"id": "n_writer", "node_type": "agent", "label": "Write Report", "agent_slot": "writer", "position": {"x": 600, "y": 200}},
                {"id": "end", "node_type": "end", "label": "End"},
            ],
            "edges": [
                {"source_node_id": "start", "target_node_id": "n_researcher"},
                {"source_node_id": "n_researcher", "target_node_id": "n_analyst"},
                {"source_node_id": "n_analyst", "target_node_id": "n_writer"},
                {"source_node_id": "n_writer", "target_node_id": "end"},
            ],
        },
    },
    {
        "id": "customer_support",
        "name": "Customer Support Bot",
        "description": "Triage agent classifies queries; Specialist handles complex cases; Escalation agent manages frustrated customers.",
        "category": "support",
        "icon": "headphones",
        "agents": [
            {
                "slot": "triage",
                "name": "Triage Bot",
                "role": "Customer support triage",
                "system_prompt": (
                    "You are a customer support triage agent. Classify the incoming customer "
                    "query as one of: 'simple' (FAQ, basic info), 'complex' (technical issue, "
                    "billing), or 'escalate' (angry customer, legal issue). "
                    "Respond with ONLY the classification word, nothing else."
                ),
                "model": "gpt-4o-mini",
                "tools": [],
                "is_telegram_agent": True,
            },
            {
                "slot": "specialist",
                "name": "Support Specialist",
                "role": "Technical support specialist",
                "system_prompt": (
                    "You are a knowledgeable support specialist. Handle technical and billing "
                    "inquiries professionally. Provide step-by-step solutions. If you cannot "
                    "resolve the issue, collect all relevant information for escalation."
                ),
                "model": "gpt-4o-mini",
                "tools": ["web_search", "get_datetime"],
            },
            {
                "slot": "escalation",
                "name": "Escalation Manager",
                "role": "Senior customer relations manager",
                "system_prompt": (
                    "You are a senior customer relations manager. Handle escalated cases with "
                    "empathy and authority. Offer appropriate compensation, clear timelines, "
                    "and direct contact. De-escalate while finding real solutions."
                ),
                "model": "gpt-4o-mini",
                "tools": [],
            },
        ],
        "graph": {
            "nodes": [
                {"id": "start", "node_type": "start", "label": "Start"},
                {"id": "n_triage", "node_type": "agent", "label": "Triage", "agent_slot": "triage", "position": {"x": 100, "y": 200}},
                {"id": "n_specialist", "node_type": "agent", "label": "Specialist", "agent_slot": "specialist", "position": {"x": 400, "y": 100}},
                {"id": "n_escalation", "node_type": "agent", "label": "Escalation", "agent_slot": "escalation", "position": {"x": 400, "y": 300}},
                {"id": "end", "node_type": "end", "label": "End"},
            ],
            "edges": [
                {"source_node_id": "start", "target_node_id": "n_triage"},
                {
                    "source_node_id": "n_triage",
                    "target_node_id": "n_escalation",
                    "condition": (
                        "list(outputs.values()) and 'escalate' in str(list(outputs.values())[-1]).lower()"
                    ),
                    "label": "escalate",
                },
                {
                    "source_node_id": "n_triage",
                    "target_node_id": "n_specialist",
                    "condition": (
                        "list(outputs.values()) and ('simple' in str(list(outputs.values())[-1]).lower() "
                        "or 'complex' in str(list(outputs.values())[-1]).lower())"
                    ),
                    "label": "simple or complex",
                },
                {"source_node_id": "n_specialist", "target_node_id": "end"},
                {"source_node_id": "n_escalation", "target_node_id": "end"},
            ],
        },
    },
    {
        "id": "content_creation",
        "name": "Content Creation Pipeline",
        "description": "Ideator generates concepts, Critic reviews quality (with feedback loop), Publisher finalizes.",
        "category": "content",
        "icon": "pen-tool",
        "agents": [
            {
                "slot": "ideator",
                "name": "Content Ideator",
                "role": "Creative content strategist",
                "system_prompt": (
                    "You are a creative content strategist. Generate compelling, original content "
                    "ideas and drafts based on the given topic. Focus on engagement, clarity, "
                    "and audience relevance. Produce a full draft."
                ),
                "model": "gpt-4o-mini",
                "tools": ["web_search"],
            },
            {
                "slot": "critic",
                "name": "Content Critic",
                "role": "Editorial quality reviewer",
                "system_prompt": (
                    "You are a strict editorial quality reviewer. Evaluate the content for "
                    "clarity, accuracy, engagement, and SEO. Rate it as 'approved' or 'revision_needed'. "
                    "If revision needed, provide specific, actionable feedback. "
                    "Start your response with APPROVED: or REVISION:"
                ),
                "model": "gpt-4o-mini",
                "tools": [],
            },
            {
                "slot": "publisher",
                "name": "Content Publisher",
                "role": "Final content editor and publisher",
                "system_prompt": (
                    "You are the final content editor. Polish the approved content, "
                    "add formatting, meta description, tags, and prepare it for publication. "
                    "Output well-formatted, ready-to-publish content."
                ),
                "model": "gpt-4o-mini",
                "tools": ["get_datetime"],
            },
        ],
        "graph": {
            "nodes": [
                {"id": "start", "node_type": "start", "label": "Start"},
                {"id": "n_ideator", "node_type": "agent", "label": "Draft Content", "agent_slot": "ideator", "position": {"x": 100, "y": 200}},
                {"id": "n_critic", "node_type": "agent", "label": "Review Quality", "agent_slot": "critic", "position": {"x": 350, "y": 200}},
                {"id": "n_publisher", "node_type": "agent", "label": "Publish", "agent_slot": "publisher", "position": {"x": 600, "y": 200}},
                {"id": "end", "node_type": "end", "label": "End"},
            ],
            "edges": [
                {"source_node_id": "start", "target_node_id": "n_ideator"},
                {"source_node_id": "n_ideator", "target_node_id": "n_critic"},
                {
                    "source_node_id": "n_critic",
                    "target_node_id": "n_ideator",
                    "condition": "'REVISION' in str(list(outputs.values())[-1]) and iteration < 3",
                    "label": "revision needed",
                },
                {
                    "source_node_id": "n_critic",
                    "target_node_id": "n_publisher",
                    "condition": "'APPROVED' in str(list(outputs.values())[-1]) or iteration >= 3",
                    "label": "approved",
                },
                {"source_node_id": "n_publisher", "target_node_id": "end"},
            ],
        },
    },
]


def get_all_templates() -> list[dict]:
    return TEMPLATES


def get_template(template_id: str) -> dict | None:
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
