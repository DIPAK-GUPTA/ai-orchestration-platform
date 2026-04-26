"""
Agent Tools Registry
--------------------
All tools that can be assigned to agents in the UI.
Each tool is a LangChain Tool that can be bound to any LLM.
"""

import json
import math
import httpx
import logging
import redis
from datetime import datetime
from typing import Optional
from langchain_core.tools import StructuredTool, Tool
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


# ─────────────── Tool input schemas ───────────────

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query")

class CalculatorInput(BaseModel):
    expression: str = Field(..., description="Math expression to evaluate")

class HttpGetInput(BaseModel):
    url: str = Field(..., description="URL to fetch")
    headers: Optional[dict] = Field(default=None, description="Optional headers")

class DateTimeInput(BaseModel):
    timezone: Optional[str] = Field(default="UTC", description="Timezone")

class JsonParseInput(BaseModel):
    json_string: str = Field(..., description="JSON string to parse")

class TextSummaryInput(BaseModel):
    text: str = Field(..., description="Text to summarize")
    max_words: int = Field(default=100, description="Max words")

class A2AInput(BaseModel):
    target_agent_id: str = Field(..., description="UUID of the other agent in this workflow")
    message: str = Field(..., description="Message to deliver asynchronously")


# ─────────────── Implementations ───────────────

def web_search_fn(query: str) -> str:
    return json.dumps({
        "query": query,
        "results": [
            {
                "title": f"Result 1 for: {query}",
                "url": "https://example.com/1",
                "snippet": f"Simulated result for '{query}' — connect a real search API in production (SerpAPI, Tavily).",
            },
        ],
    })


def calculator_fn(expression: str) -> str:
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error evaluating '{expression}': {e!s}"


def http_get_fn(url: str, headers: Optional[dict] = None) -> str:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers or {})
            return json.dumps({
                "status": response.status_code,
                "content": response.text[:2000],
                "headers": dict(response.headers),
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_datetime_fn(timezone: str = "UTC") -> str:
    now = datetime.utcnow()
    return json.dumps({
        "utc": now.isoformat(),
        "unix": int(now.timestamp()),
        "formatted": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    })


def json_parse_fn(json_string: str) -> str:
    try:
        parsed = json.loads(json_string)
        return json.dumps(parsed, indent=2)
    except Exception as e:
        return f"JSON parse error: {e!s}"


def text_summary_fn(text: str, max_words: int = 100) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def _send_a2a_sync(execution_id: str, from_agent_id: str, target_agent_id: str, message: str) -> str:
    from app.services.a2a_persist import record_a2a_message

    message_id: str | None = None
    if execution_id and from_agent_id:
        message_id = record_a2a_message(execution_id, from_agent_id, target_agent_id, message)
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        payload = {
            "type": "a2a_message",
            "execution_id": execution_id,
            "from_agent_id": from_agent_id,
            "to_agent_id": target_agent_id,
            "message": message,
            "message_id": message_id,
            "at": datetime.utcnow().isoformat() + "Z",
        }
        s = json.dumps(payload)
        if execution_id:
            r.publish(f"execution:{execution_id}", s)
            r.rpush(f"execution:{execution_id}:a2a", s)
            r.ltrim(f"execution:{execution_id}:a2a", -200, -1)
            r.expire(f"execution:{execution_id}:a2a", 86400)
        r.close()
    except Exception as e:
        logger.warning("A2A publish error: %s", e)
    return json.dumps({
        "ok": True,
        "to": target_agent_id,
        "message_preview": message[:200],
        "asynchronous": True,
        "message_id": message_id,
    })


def _build_send_a2a_tool(execution_id: str, from_agent_id: str) -> StructuredTool:
    def _run(target_agent_id: str, message: str) -> str:
        return _send_a2a_sync(execution_id, from_agent_id, target_agent_id, message)
    return StructuredTool.from_function(
        func=_run,
        name="send_agent_message",
        description="Send a message to another agent in the same workflow. Messages are delivered asynchronously and appear in execution logs and monitoring.",
        args_schema=A2AInput,
    )


TOOL_REGISTRY: dict[str, Tool] = {
    "web_search": StructuredTool.from_function(
        func=web_search_fn,
        name="web_search",
        description="Search the web for information. Returns top results with titles and snippets.",
        args_schema=WebSearchInput,
    ),
    "calculator": StructuredTool.from_function(
        func=calculator_fn,
        name="calculator",
        description="Evaluate mathematical expressions. Supports all math operations and functions.",
        args_schema=CalculatorInput,
    ),
    "http_get": StructuredTool.from_function(
        func=http_get_fn,
        name="http_get",
        description="Make an HTTP GET request to a URL and return the response.",
        args_schema=HttpGetInput,
    ),
    "get_datetime": StructuredTool.from_function(
        func=get_datetime_fn,
        name="get_datetime",
        description="Get the current date and time in UTC.",
        args_schema=DateTimeInput,
    ),
    "json_parse": StructuredTool.from_function(
        func=json_parse_fn,
        name="json_parse",
        description="Parse a JSON string and return formatted JSON.",
        args_schema=JsonParseInput,
    ),
    "text_summary": StructuredTool.from_function(
        func=text_summary_fn,
        name="text_summary",
        description="Summarize a long text by extracting the first N words.",
        args_schema=TextSummaryInput,
    ),
}


AVAILABLE_TOOLS = [
    {"id": "web_search", "name": "Web Search", "description": "Search the web for information", "category": "research"},
    {"id": "calculator", "name": "Calculator", "description": "Evaluate mathematical expressions", "category": "utility"},
    {"id": "http_get", "name": "HTTP GET", "description": "Make HTTP GET requests to APIs", "category": "integration"},
    {"id": "get_datetime", "name": "Date & Time", "description": "Get current date and time", "category": "utility"},
    {"id": "json_parse", "name": "JSON Parser", "description": "Parse and format JSON data", "category": "utility"},
    {"id": "text_summary", "name": "Text Summary", "description": "Summarize long texts", "category": "nlp"},
    {"id": "send_agent_message", "name": "Agent Messenger", "description": "Asynchronously message another agent in a workflow", "category": "collaboration"},
]


def get_agent_tools(
    tool_names: list[str],
    tool_context: dict[str, str] | None = None,
) -> list[Tool | StructuredTool]:
    tool_context = tool_context or {}
    eid = tool_context.get("execution_id", "")
    from_id = tool_context.get("from_agent_id", "")
    out: list[Tool] = []
    for name in tool_names:
        if name == "send_agent_message":
            out.append(_build_send_a2a_tool(eid, from_id))
        elif name in TOOL_REGISTRY:
            out.append(TOOL_REGISTRY[name])
    return out
