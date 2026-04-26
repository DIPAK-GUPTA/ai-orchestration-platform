"""
LangGraph Runtime
-----------------
Builds and executes LangGraph StateGraphs from workflow definitions.
Runtime choice: **LangGraph** — StateGraph, conditional edges, async execution, checkpointing.
See README for justification.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, TypedDict, Annotated
import operator

import redis
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.agents.tools import get_agent_tools
from app.agents.memory import AgentMemory

logger = logging.getLogger(__name__)


def merge_agent_invocations(
    left: dict[str, int] | None,
    right: dict[str, int] | None,
) -> dict[str, int]:
    m = dict(left) if left else {}
    for k, v in (right or {}).items():
        m[k] = m.get(k, 0) + int(v or 0)
    return m


class WorkflowState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    current_agent: str
    execution_id: str
    workflow_id: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    agent_outputs: dict[str, Any]
    token_usage: dict[str, int]
    errors: list[str]
    iteration_count: int
    completed: bool
    channel: str
    agent_invocations: Annotated[dict[str, int], merge_agent_invocations]


def _concat_human_text(messages: list[BaseMessage]) -> str:
    out: list[str] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            c = m.content
            if isinstance(c, str):
                out.append(c)
    return " ".join(out).lower()


def _topic_guard_violation(text: str, guardrails: dict[str, Any]) -> str | None:
    t = (text or "").lower()
    for b in guardrails.get("blocked_topics") or []:
        if b and str(b).lower() in t:
            return f"I cannot help with that (blocked topic: {b!r})."
    allowed = guardrails.get("allowed_topics") or []
    if allowed and not any(str(a) and str(a).lower() in t for a in allowed):
        return "I can only discuss topics in the allowed list configured for this agent."
    return None


def _rate_limit_allows(agent_id: str, per_minute: int) -> bool:
    if not per_minute or per_minute < 1 or per_minute > 1_000_000:
        return True
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        b = int(time.time()) // 60
        k = f"guard:rl:{agent_id}:{b}"
        n = r.incr(k)
        r.expire(k, 120)
        return n <= per_minute
    except Exception as e:
        logger.warning("Rate limit check failed: %s", e)
        return True
    finally:
        r.close()


def _extract_tool_call(tc: Any) -> tuple[str, dict] | None:
    if isinstance(tc, dict):
        name = tc.get("name")
        args = tc.get("args")
        if args is None and "arguments" in tc:
            try:
                args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
            except Exception:
                args = {}
        if name:
            return name, args or {}
    name = getattr(tc, "name", None)
    args = getattr(tc, "args", None) or {}
    if name:
        return name, args
    return None


def build_agent_node(
    agent_config: dict,
    log_callback: Callable | None = None,
) -> Callable:
    agent_id = agent_config["id"]
    name = agent_config["name"]
    system_prompt = agent_config["system_prompt"]
    model_name = agent_config.get("model", settings.openai_model)
    tool_names = agent_config.get("tools", [])
    memory_config = agent_config.get("memory_config", {})
    guardrails: dict = agent_config.get("guardrails") or {}
    skills = agent_config.get("skills") or []
    interaction_rules: dict = agent_config.get("interaction_rules") or {}

    max_tok = int(guardrails.get("max_tokens_per_turn") or 0) or 2000
    if max_tok < 1:
        max_tok = 2000
    if max_tok > 32_000:
        max_tok = 32_000
    max_agent_turns = int(guardrails.get("max_turns") or 0) or 50

    memory = AgentMemory(agent_id=agent_id, config=memory_config)

    async def agent_node(state: WorkflowState) -> dict:
        execution_id = state["execution_id"]
        messages = state["messages"]
        inv_so_far = (state.get("agent_invocations") or {}).get(agent_id, 0)
        if inv_so_far >= max_agent_turns:
            msg = "[Guardrail] This agent has reached the configured maximum number of turns."
            return {
                "messages": [AIMessage(content=msg, name=agent_id)],
                "current_agent": agent_id,
                "agent_outputs": {**state.get("agent_outputs", {}), agent_id: msg},
                "token_usage": state.get("token_usage", {}),
                "iteration_count": state.get("iteration_count", 0) + 1,
                "agent_invocations": {agent_id: 0},
            }

        if not _rate_limit_allows(
            agent_id, int(guardrails.get("rate_limit_per_minute", 0) or 0)
        ):
            msg = "[Guardrail] Rate limit exceeded for this agent. Try again shortly."
            return {
                "messages": [AIMessage(content=msg, name=agent_id)],
                "current_agent": agent_id,
                "agent_outputs": {**state.get("agent_outputs", {}), agent_id: msg},
                "token_usage": state.get("token_usage", {}),
                "iteration_count": state.get("iteration_count", 0) + 1,
                "agent_invocations": {agent_id: 0},
            }

        base_prompt = system_prompt
        if skills:
            base_prompt = f"{base_prompt}\n\nConfigured skills: {', '.join(skills)}"
        if interaction_rules:
            try:
                ir = json.dumps(interaction_rules, indent=2)[:6000]
                base_prompt = f"{base_prompt}\n\nInteraction rules:\n{ir}"
            except (TypeError, ValueError):
                pass

        tool_context = {"execution_id": execution_id, "from_agent_id": agent_id}
        tools = get_agent_tools(tool_names, tool_context=tool_context)
        llm = _build_llm(model_name, max_output_tokens=max_tok)
        llm_with_tools = llm.bind_tools(tools) if tools else llm

        if log_callback:
            await log_callback(
                execution_id=execution_id,
                agent_id=agent_id,
                event="agent_start",
                message=f"Agent '{name}' starting turn",
                level="info",
            )

        context_messages = [SystemMessage(content=base_prompt)]
        memory_context = await memory.load()
        if memory_context:
            context_messages.append(SystemMessage(content=f"Memory context:\n{memory_context}"))

        relevant = messages[-10:] if len(messages) > 10 else messages
        top_violation = _topic_guard_violation(_concat_human_text(relevant), guardrails)
        if top_violation:
            return {
                "messages": [AIMessage(content=top_violation, name=agent_id)],
                "current_agent": agent_id,
                "agent_outputs": {**state.get("agent_outputs", {}), agent_id: top_violation},
                "token_usage": state.get("token_usage", {}),
                "iteration_count": state.get("iteration_count", 0) + 1,
                "agent_invocations": {agent_id: 0},
            }

        context_messages.extend(relevant)

        try:
            response = await llm_with_tools.ainvoke(context_messages)
            tool_map = {t.name: t for t in tools}
            tool_messages: list[BaseMessage] = []
            tcalls = getattr(response, "tool_calls", None) or []
            for tc in tcalls:
                ext = _extract_tool_call(tc)
                if not ext:
                    continue
                tool_name, tool_args = ext
                t = tool_map.get(tool_name)
                if not t:
                    continue
                try:
                    if hasattr(t, "ainvoke"):
                        result = await t.ainvoke(tool_args)
                    elif hasattr(t, "invoke"):
                        result = t.invoke(tool_args)
                    else:
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: str(t),
                        )
                except Exception as e:
                    result = f"Tool {tool_name} error: {e!s}"
                tc_id = ""
                if isinstance(tc, dict):
                    tc_id = str(tc.get("id") or "")
                else:
                    tc_id = str(getattr(tc, "id", None) or "")
                tool_messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tc_id or f"call_{tool_name}",
                        name=tool_name,
                    )
                )

            if tool_messages:
                final = await llm.ainvoke([*context_messages, response, *tool_messages])
                content = (final.content or "").strip() or (response.content or "")
            else:
                content = response.content or ""
                final = response

            tokens_used = 0
            um = getattr(response, "usage_metadata", None) or {}
            if isinstance(um, dict) and um:
                tokens_used = um.get("total_tokens", 0)
            fum = getattr(final, "usage_metadata", None) or {}
            if not tokens_used and isinstance(fum, dict):
                tokens_used = fum.get("total_tokens", 0)
            cost = _estimate_cost(model_name, tokens_used)

            await memory.save(f"Turn result: {content[:500]}")

            if log_callback:
                await log_callback(
                    execution_id=execution_id,
                    agent_id=agent_id,
                    event="agent_complete",
                    message=f"Agent '{name}' completed turn",
                    level="info",
                    data={"output_preview": (content or "")[:200], "tokens": tokens_used, "cost": cost},
                    tokens_used=tokens_used,
                    cost_usd=cost,
                )

            new_message = AIMessage(content=content or " ", name=agent_id)
            agent_outputs = dict(state.get("agent_outputs", {}))
            agent_outputs[agent_id] = content
            token_usage = dict(state.get("token_usage", {}))
            token_usage[agent_id] = token_usage.get(agent_id, 0) + tokens_used
            return {
                "messages": [new_message],
                "current_agent": agent_id,
                "agent_outputs": agent_outputs,
                "token_usage": token_usage,
                "iteration_count": state.get("iteration_count", 0) + 1,
                "agent_invocations": {agent_id: 1},
            }

        except Exception as e:
            logger.error("Agent %s error: %s", name, e, exc_info=True)
            if log_callback:
                await log_callback(
                    execution_id=execution_id,
                    agent_id=agent_id,
                    event="agent_error",
                    message=f"Agent '{name}' error: {e!s}",
                    level="error",
                )
            errors = list(state.get("errors", []))
            errors.append(f"{name}: {e!s}")
            return {
                "errors": errors,
                "current_agent": agent_id,
                "agent_invocations": {agent_id: 0},
            }

    return agent_node


def build_condition_router(condition_expr: str, routes: dict[str, str]) -> Callable:
    def router(state: WorkflowState) -> str:
        try:
            result = eval(  # noqa: S102 — workflow author expressions from trusted UI/DB
                condition_expr,
                {
                    "state": state,
                    "outputs": state.get("agent_outputs", {}),
                    "iteration": state.get("iteration_count", 0),
                    "errors": state.get("errors", []),
                    "completed": state.get("completed", False),
                },
            )
            return routes.get(str(result), END)
        except Exception as e:
            logger.error("Condition eval error: %s", e)
            return END
    return router


class WorkflowGraph:
    def __init__(self, workflow_config: dict, agents: list[dict], log_callback: Callable | None = None):
        self.workflow_config = workflow_config
        self.agents = {a["id"]: a for a in agents}
        self.log_callback = log_callback
        self.checkpointer = MemorySaver()
        self.graph = None

    def build(self) -> "WorkflowGraph":
        graph = StateGraph(WorkflowState)
        nodes = self.workflow_config.get("nodes", [])
        edges = self.workflow_config.get("edges", [])

        node_id_map: dict[str, Any] = {}
        for node in nodes:
            node_id = node["id"]
            node_type = node.get("node_type", "agent")
            agent_id = node.get("agent_id")

            if node_type == "start":
                node_id_map[node_id] = START
            elif node_type == "end":
                node_id_map[node_id] = END
            elif node_type == "agent" and agent_id and agent_id in self.agents:
                agent_config = self.agents[agent_id]
                agent_fn = build_agent_node(agent_config, self.log_callback)
                gname = f"agent_{agent_id[:8]}"
                graph.add_node(gname, agent_fn)
                node_id_map[node_id] = gname
            elif node_type == "condition":
                node_id_map[node_id] = node_id

        conditional_sources: dict[str, list] = {}
        for edge in edges:
            src = edge["source_node_id"]
            tgt = edge["target_node_id"]
            condition = edge.get("condition")
            label = edge.get("label", "")

            src_node = node_id_map.get(src, src)
            tgt_node = node_id_map.get(tgt, END)

            if condition:
                if src_node not in conditional_sources:
                    conditional_sources[src_node] = []
                conditional_sources[src_node].append(
                    {"condition": condition, "target": tgt_node, "label": label}
                )
            else:
                if src_node == START:
                    graph.add_edge(START, tgt_node)
                elif tgt_node == END:
                    graph.add_edge(src_node, END)
                else:
                    graph.add_edge(src_node, tgt_node)

        for src_node, cond_edges in conditional_sources.items():
            path_map: dict[str, Any] = {}
            conditions_list = []
            for i, ce in enumerate(cond_edges):
                key = f"route_{i}"
                path_map[key] = ce["target"]
                conditions_list.append((ce["condition"], key))

            def make_router(conds, pm: dict) -> Any:
                def _router(state: WorkflowState) -> str:
                    for expr, rkey in conds:
                        try:
                            if eval(  # noqa: S102
                                expr,
                                {
                                    "state": state,
                                    "outputs": state.get("agent_outputs", {}),
                                    "iteration": state.get("iteration_count", 0),
                                    "errors": state.get("errors", []),
                                },
                            ):
                                return rkey
                        except Exception:
                            continue
                    return list(pm.keys())[0] if pm else "route_0"

                return _router

            gr = make_router(conditions_list, path_map)
            graph.add_conditional_edges(src_node, gr, path_map)

        self.graph = graph.compile(checkpointer=self.checkpointer)
        return self

    async def run(
        self,
        execution_id: str,
        workflow_id: str,
        input_data: dict,
        channel: str = "internal",
    ) -> dict:
        if not self.graph:
            raise RuntimeError("Graph not built. Call .build() first.")

        im = input_data.get("message", "Start workflow")
        initial_state: WorkflowState = {
            "messages": [HumanMessage(content=im)],
            "current_agent": "",
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "input_data": input_data,
            "output_data": {},
            "agent_outputs": {},
            "token_usage": {},
            "errors": [],
            "iteration_count": 0,
            "completed": False,
            "channel": channel,
            "agent_invocations": {},
        }
        config = {"configurable": {"thread_id": execution_id}}
        if self.log_callback:
            await self.log_callback(
                execution_id=execution_id,
                agent_id=None,
                event="graph_invoke",
                message="Running LangGraph ainvoke",
                level="info",
            )

        final: dict[str, Any] = await self.graph.ainvoke(initial_state, config)
        if not final:
            return {"status": "completed", "output": {}, "errors": [], "token_usage": {}, "messages": []}

        def _m_text(m: Any) -> str:
            c = getattr(m, "content", m)
            return c if isinstance(c, str) else str(c)

        return {
            "status": "completed",
            "output": final.get("agent_outputs", {}),
            "errors": final.get("errors", []),
            "token_usage": final.get("token_usage", {}),
            "messages": [_m_text(m) for m in final.get("messages", [])],
        }


def _build_llm(model_name: str, max_output_tokens: int | None = None):
    tok = max_output_tokens if max_output_tokens and max_output_tokens > 0 else None
    if model_name.startswith("gpt"):
        kwargs: dict[str, Any] = {
            "model": model_name,
            "api_key": settings.openai_api_key,
            "temperature": 0.7,
        }
        if tok:
            kwargs["max_tokens"] = tok
        return ChatOpenAI(**kwargs)
    if model_name.startswith("claude"):
        from langchain_anthropic import ChatAnthropic  # type: ignore

        kwargs = {
            "model": model_name,
            "api_key": settings.anthropic_api_key,
            "temperature": 0.7,
        }
        if tok:
            kwargs["max_tokens"] = tok
        return ChatAnthropic(**kwargs)  # type: ignore[misc]
    kwargs = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.7,
    }
    if tok:
        kwargs["max_tokens"] = tok
    return ChatOpenAI(**kwargs)


def _estimate_cost(model_name: str, tokens: int) -> float:
    cost_per_1k = {
        "gpt-4o": 0.005,
        "gpt-4o-mini": 0.00015,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.0005,
        "claude-3-5-sonnet-20241022": 0.003,
        "claude-3-haiku-20240307": 0.00025,
    }
    rate = cost_per_1k.get(model_name, 0.001)
    return round((tokens / 1000) * rate, 6)
