import axios from "axios";

const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: base,
  headers: { "Content-Type": "application/json" },
});

export const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type Agent = {
  id: string;
  name: string;
  role: string;
  system_prompt: string;
  model: string;
  status: string;
  tools: string[];
  skills: string[];
  memory_config: Record<string, unknown>;
  guardrails: Record<string, unknown>;
  schedule: Record<string, unknown> | null;
  interaction_rules: Record<string, unknown>;
  channel_config: Record<string, unknown>;
  is_telegram_agent: boolean;
  telegram_chat_id: string | null;
  created_at: string;
  updated_at: string;
};

export type Workflow = {
  id: string;
  name: string;
  description: string;
  status: string;
  template_id: string | null;
  graph_definition: Record<string, unknown>;
  node_positions: Record<string, unknown>;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created_at: string;
  updated_at: string;
};

export type WorkflowNode = {
  id: string;
  agent_id: string | null;
  node_type: string;
  label: string;
  config: Record<string, unknown>;
  position_x: number;
  position_y: number;
};

export type WorkflowEdge = {
  id: string;
  source_node_id: string;
  target_node_id: string;
  condition: string | null;
  label: string;
};

export type Execution = {
  id: string;
  workflow_id: string;
  status: string;
  trigger: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown> | null;
  error: string | null;
  total_tokens: number;
  total_cost_usd: number;
  started_at: string;
  completed_at: string | null;
  logs: Array<{
    id: string;
    agent_id: string | null;
    level: string;
    event: string;
    message: string;
    data: Record<string, unknown>;
    tokens_used: number;
    cost_usd: number;
    created_at: string;
  }>;
};
