import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import (
    String, Text, Boolean, DateTime, JSON, ForeignKey,
    Enum as SAEnum, Integer, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class AgentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    running = "running"
    error = "error"


class WorkflowStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class ExecutionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    agent = "agent"


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini")
    status: Mapped[AgentStatus] = mapped_column(SAEnum(AgentStatus), default=AgentStatus.active)

    tools: Mapped[list] = mapped_column(JSONB, default=list)
    skills: Mapped[list] = mapped_column(JSONB, default=list)  # named capabilities / SOPs
    memory_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    guardrails: Mapped[dict] = mapped_column(JSONB, default=dict)
    schedule: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    interaction_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    channel_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_telegram_agent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow_nodes: Mapped[list["WorkflowNode"]] = relationship("WorkflowNode", back_populates="agent")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="agent")
    logs: Mapped[list["ExecutionLog"]] = relationship("ExecutionLog", back_populates="agent")


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[WorkflowStatus] = mapped_column(SAEnum(WorkflowStatus), default=WorkflowStatus.draft)
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    graph_definition: Mapped[dict] = mapped_column(JSONB, default=dict)
    node_positions: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    nodes: Mapped[list["WorkflowNode"]] = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    edges: Mapped[list["WorkflowEdge"]] = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")
    executions: Mapped[list["WorkflowExecution"]] = relationship("WorkflowExecution", back_populates="workflow")


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"))
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    node_type: Mapped[str] = mapped_column(String(32), default="agent")
    label: Mapped[str] = mapped_column(String(128), default="")
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="nodes")
    agent: Mapped["Agent | None"] = relationship("Agent", back_populates="workflow_nodes")


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"))
    source_node_id: Mapped[str] = mapped_column(String(36))
    target_node_id: Mapped[str] = mapped_column(String(36))
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str] = mapped_column(String(64), default="")

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="edges")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"))
    status: Mapped[ExecutionStatus] = mapped_column(SAEnum(ExecutionStatus), default=ExecutionStatus.pending)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")
    logs: Mapped[list["ExecutionLog"]] = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="execution")


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_executions.id", ondelete="CASCADE"))
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    event: Mapped[str] = mapped_column(String(64), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    execution: Mapped["WorkflowExecution"] = relationship("WorkflowExecution", back_populates="logs")
    agent: Mapped["Agent | None"] = relationship("Agent", back_populates="logs")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflow_executions.id"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)

    channel: Mapped[str] = mapped_column(String(32), default="internal")
    channel_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    from_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    to_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    message_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    execution: Mapped["WorkflowExecution | None"] = relationship("WorkflowExecution", back_populates="messages")
    agent: Mapped["Agent | None"] = relationship("Agent", back_populates="messages")
