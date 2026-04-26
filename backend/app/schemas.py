from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    running = "running"
    error = "error"


class MemoryConfig(BaseModel):
    type: str = "buffer"
    max_tokens: int = 4096
    persist: bool = True


class GuardrailConfig(BaseModel):
    max_tokens_per_turn: int = 2000
    max_turns: int = 50
    allowed_topics: list[str] = []
    blocked_topics: list[str] = []
    # 0 = off (workflows can call many steps per minute)
    rate_limit_per_minute: int = 0


class ScheduleConfig(BaseModel):
    enabled: bool = False
    cron: Optional[str] = None
    timezone: str = "UTC"
    trigger_prompt: Optional[str] = None


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=256)
    system_prompt: str = Field(..., min_length=1)
    model: str = "gpt-4o-mini"
    tools: list[str] = []
    skills: list[str] = []
    memory_config: MemoryConfig = MemoryConfig()
    guardrails: GuardrailConfig = GuardrailConfig()
    schedule: Optional[ScheduleConfig] = None
    interaction_rules: dict[str, Any] = {}
    channel_config: dict[str, Any] = {}
    is_telegram_agent: bool = False
    telegram_chat_id: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    memory_config: Optional[MemoryConfig] = None
    guardrails: Optional[GuardrailConfig] = None
    schedule: Optional[ScheduleConfig] = None
    interaction_rules: Optional[dict[str, Any]] = None
    channel_config: Optional[dict[str, Any]] = None
    is_telegram_agent: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    status: Optional[AgentStatus] = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    role: str
    system_prompt: str
    model: str
    status: AgentStatus
    tools: list[str]
    skills: list[str] = []
    memory_config: dict[str, Any]
    guardrails: dict[str, Any]
    schedule: Optional[dict[str, Any]]
    interaction_rules: dict[str, Any]
    channel_config: dict[str, Any]
    is_telegram_agent: bool
    telegram_chat_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class NodePosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class WorkflowNodeCreate(BaseModel):
    id: Optional[str] = None
    agent_id: Optional[str] = None
    node_type: str = "agent"
    label: str = ""
    config: dict[str, Any] = {}
    position: NodePosition = NodePosition()


class WorkflowEdgeCreate(BaseModel):
    id: Optional[str] = None
    source_node_id: str
    target_node_id: str
    condition: Optional[str] = None
    label: str = ""


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    template_id: Optional[str] = None
    nodes: list[WorkflowNodeCreate] = []
    edges: list[WorkflowEdgeCreate] = []
    graph_definition: dict[str, Any] = {}
    node_positions: dict[str, Any] = {}


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    nodes: Optional[list[WorkflowNodeCreate]] = None
    edges: Optional[list[WorkflowEdgeCreate]] = None
    graph_definition: Optional[dict[str, Any]] = None
    node_positions: Optional[dict[str, Any]] = None


class WorkflowNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: Optional[str]
    node_type: str
    label: str
    config: dict[str, Any]
    position_x: float
    position_y: float


class WorkflowEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_node_id: str
    target_node_id: str
    condition: Optional[str]
    label: str


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    status: str
    template_id: Optional[str]
    graph_definition: dict[str, Any]
    node_positions: dict[str, Any]
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]
    created_at: datetime
    updated_at: datetime


class ExecutionCreate(BaseModel):
    workflow_id: str
    input_data: dict[str, Any] = {}
    trigger: str = "manual"


class ExecutionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: Optional[str]
    level: str
    event: str
    message: str
    data: dict[str, Any]
    tokens_used: int
    cost_usd: float
    created_at: datetime


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    status: str
    trigger: str
    input_data: dict[str, Any]
    output_data: Optional[dict[str, Any]]
    error: Optional[str]
    total_tokens: int
    total_cost_usd: float
    started_at: datetime
    completed_at: Optional[datetime]
    logs: list[ExecutionLogResponse] = []


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    execution_id: Optional[str]
    agent_id: Optional[str]
    channel: str
    from_agent_id: Optional[str]
    to_agent_id: Optional[str]
    role: str
    content: str
    message_metadata: dict[str, Any]
    created_at: datetime
