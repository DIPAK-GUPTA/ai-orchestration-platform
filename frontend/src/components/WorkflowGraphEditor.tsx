"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  ReactFlowProvider,
  type Connection,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api, type Agent, type Workflow } from "@/lib/api";

type NodeData = {
  label: string;
  nodeType: "start" | "end" | "agent";
  agentId?: string | null;
};

type EdgeData = { condition: string; label: string };
type WfNode = Node<NodeData>;

function toFlow(
  wf: Workflow,
  _agentList: Agent[]
): { nodes: WfNode[]; edges: Edge<EdgeData>[] } {
  const nodes: WfNode[] = (wf.nodes || []).map((n) => ({
    id: n.id,
    position: { x: n.position_x || 0, y: n.position_y || 0 },
    data: {
      label: n.label || n.node_type,
      nodeType: (n.node_type as NodeData["nodeType"]) || "agent",
      agentId: n.agent_id,
    },
  }));
  const edges: Edge<EdgeData>[] = (wf.edges || []).map((e) => {
    const cond = (e as { condition?: string | null }).condition;
    return {
      id: e.id,
      source: e.source_node_id,
      target: e.target_node_id,
      label: e.label || (cond ? "if" : undefined),
      data: { condition: cond || "", label: e.label || "" } satisfies EdgeData,
    };
  });
  void _agentList;
  return { nodes, edges };
}

const newId = () => globalThis.crypto?.randomUUID?.() ?? `id-${Date.now()}-${Math.random()}`;

const defaultNew = (): { nodes: WfNode[]; edges: Edge<EdgeData>[] } => {
  const s = newId();
  const a = newId();
  const t = newId();
  return {
    nodes: [
      { id: s, position: { x: 40, y: 120 }, data: { label: "Start", nodeType: "start" } },
      { id: a, position: { x: 320, y: 120 }, data: { label: "Agent", nodeType: "agent", agentId: null } },
      { id: t, position: { x: 600, y: 120 }, data: { label: "End", nodeType: "end" } },
    ],
    edges: [
      { id: newId(), source: s, target: a, data: { condition: "", label: "" } },
      { id: newId(), source: a, target: t, data: { condition: "", label: "" } },
    ],
  };
};

type Props = {
  workflowId?: string;
  onCancel?: () => void;
  onSaved?: (id: string) => void;
};

export function WorkflowGraphEditor({ workflowId, onCancel, onSaved }: Props) {
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<{
    type: "node" | "edge" | null;
    id: string | null;
  }>({ type: null, id: null });
  const [agents, setAgents] = useState<Agent[]>([]);
  const [name, setName] = useState("New workflow");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<WfNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge<EdgeData>>([]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const r = await api.get<Agent[]>("/api/agents");
        if (active) setAgents(r.data);
      } catch {
        if (active) setLoadErr("Could not load agents");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!workflowId) {
      const d = defaultNew();
      setNodes(d.nodes);
      setEdges(d.edges);
      setName("New workflow");
      setDescription("");
      return;
    }
    let active = true;
    (async () => {
      try {
        const [wRes, aRes] = await Promise.all([
          api.get<Workflow>(`/api/workflows/${workflowId}`),
          api.get<Agent[]>("/api/agents").catch(() => ({ data: [] as Agent[] })),
        ]);
        if (!active) return;
        setAgents(aRes.data);
        const { nodes: n, edges: e } = toFlow(wRes.data, aRes.data);
        if (n.length) {
          setNodes(n);
          setEdges(e);
        } else {
          const d = defaultNew();
          setNodes(d.nodes);
          setEdges(d.edges);
        }
        setName(wRes.data.name);
        setDescription(wRes.data.description || "");
        setLoadErr(null);
      } catch {
        if (active) setLoadErr("Workflow not found");
      }
    })();
    return () => {
      active = false;
    };
  }, [workflowId, setNodes, setEdges]);

  const onConnect = useCallback(
    (p: Connection) => {
      setEdges((es) => addEdge({ ...p, id: newId(), data: { condition: "", label: "" } as EdgeData }, es));
    },
    [setEdges]
  );

  const selectedNode = useMemo(
    () => (selected.id ? nodes.find((n) => n.id === selected.id) : null),
    [selected, nodes]
  );
  const selectedEdge = useMemo(
    () => (selected.id ? edges.find((e) => e.id === selected.id) : null),
    [selected, edges]
  );

  const addNode = (nodeType: NodeData["nodeType"]) => {
    const id = newId();
    setNodes((ns) => [
      ...ns,
      {
        id,
        position: { x: 200 + (ns.length % 4) * 60, y: 80 + (ns.length % 2) * 100 },
        data: {
          label: nodeType === "agent" ? "Agent" : nodeType === "start" ? "Start" : "End",
          nodeType,
          agentId: nodeType === "agent" ? null : null,
        },
      },
    ]);
  };

  function validate(): string | null {
    const starts = nodes.filter((n) => n.data.nodeType === "start");
    const ens = nodes.filter((n) => n.data.nodeType === "end");
    if (starts.length !== 1) return "Exactly one start node is required.";
    if (ens.length !== 1) return "Exactly one end node is required.";
    for (const n of nodes) {
      if (n.data.nodeType === "agent" && !n.data.agentId) {
        return `Agent node “${n.data.label}” must be linked to a saved agent.`;
      }
    }
    return null;
  }

  async function save() {
    const v = validate();
    if (v) {
      alert(v);
      return;
    }
    setSaving(true);
    try {
      const bodyNodes = nodes.map((n) => ({
        id: n.id,
        node_type: n.data.nodeType,
        label: n.data.label,
        agent_id: n.data.nodeType === "agent" ? n.data.agentId : null,
        config: {} as Record<string, unknown>,
        position: { x: n.position.x, y: n.position.y },
      }));
      const bodyEdges = edges.map((e) => {
        const d = (e.data as EdgeData | undefined) || { condition: "", label: "" };
        return {
          id: e.id,
          source_node_id: e.source,
          target_node_id: e.target,
          condition: d.condition?.trim() || null,
          label: d.label || "",
        };
      });

      if (workflowId) {
        await api.patch(`/api/workflows/${workflowId}`, {
          name: name || "Workflow",
          description,
          nodes: bodyNodes,
          edges: bodyEdges,
        });
        onSaved?.(workflowId);
      } else {
        const res = await api.post<Workflow>("/api/workflows", {
          name: name || "Workflow",
          description,
          graph_definition: { nodes: bodyNodes, edges: bodyEdges },
          nodes: bodyNodes,
          edges: bodyEdges,
        });
        onSaved?.(res.data.id);
      }
    } catch (e) {
      console.error(e);
      alert("Save failed. Check the API and that your graph is valid.");
    } finally {
      setSaving(false);
    }
  }

  const updateSelectedNode = (p: { label?: string; agentId?: string | null }) => {
    if (selectedNode && selected.id) {
      setNodes((ns) =>
        ns.map((n) => {
          if (n.id !== selected.id) return n;
          return {
            ...n,
            data: {
              ...n.data,
              ...(p.label != null ? { label: p.label } : {}),
              ...(p.agentId !== undefined ? { agentId: p.agentId } : {}),
            },
          };
        })
      );
    }
  };

  const updateSelectedEdge = (p: { condition: string; label: string }) => {
    if (selectedEdge && selected.id) {
      setEdges((es) =>
        es.map((e) => {
          if (e.id !== selected.id) return e;
          return { ...e, data: p, label: p.label || (p.condition ? "if" : undefined) };
        })
      );
    }
  };

  return (
    <div className="space-y-4">
      {loadErr && <p className="text-amber-400 text-sm">{loadErr}</p>}
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-300">
          Name
          <input
            className="input mt-1 block w-64"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="text-sm text-slate-300 grow min-w-[12rem]">
          Description
          <input
            className="input mt-1 block w-full"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
      </div>
      <p className="text-xs text-slate-500">
        Connect start → one or more agents → end. For routing, add two edges from the same node
        and set a Python <strong>condition</strong> on each (use <code>outputs</code>, <code>iteration</code>).
      </p>
      <div className="grid gap-4 md:grid-cols-[1fr,18rem]">
        <div className="h-[min(60vh,520px)] overflow-hidden rounded-lg border border-slate-800 bg-slate-950/50">
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              fitView
              onNodeClick={(_, n) => setSelected({ type: "node", id: n.id })}
              onEdgeClick={(_, e) => setSelected({ type: "edge", id: e.id })}
              onPaneClick={() => setSelected({ type: null, id: null })}
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </ReactFlowProvider>
        </div>
        <div className="space-y-3 text-sm">
          <p className="text-xs font-semibold uppercase text-slate-500">Palette</p>
          <div className="flex flex-col gap-2">
            <button type="button" className="btn w-full" onClick={() => addNode("start")}>
              + Start
            </button>
            <button type="button" className="btn w-full" onClick={() => addNode("end")}>
              + End
            </button>
            <button type="button" className="btn w-full" onClick={() => addNode("agent")}>
              + Agent
            </button>
          </div>
          {selectedNode && (
            <div className="card space-y-2">
              <h3 className="text-slate-300">Node: {selectedNode.id.slice(0, 8)}…</h3>
              <p className="text-xs text-slate-500">Type: {selectedNode.data.nodeType}</p>
              {selectedNode.data.nodeType === "agent" && (
                <>
                  <label className="block text-slate-400 text-xs">Label</label>
                  <input
                    className="input w-full"
                    value={selectedNode.data.label}
                    onChange={(e) => updateSelectedNode({ label: e.target.value })}
                  />
                  <label className="block text-slate-400 text-xs">Agent</label>
                  <select
                    className="input w-full"
                    value={selectedNode.data.agentId || ""}
                    onChange={(e) => updateSelectedNode({ agentId: e.target.value || null })}
                  >
                    <option value="">Select agent…</option>
                    {agents.map((ag) => (
                      <option key={ag.id} value={ag.id}>
                        {ag.name}
                      </option>
                    ))}
                  </select>
                </>
              )}
            </div>
          )}
          {selectedEdge && (
            <div className="card space-y-2">
              <h3 className="text-slate-300">Edge (branch)</h3>
              <label className="block text-xs text-slate-500">
                Label
                <input
                  className="input mt-1 w-full font-mono"
                  value={(selectedEdge.data as EdgeData | undefined)?.label || ""}
                  onChange={(e) =>
                    updateSelectedEdge({
                      condition: (selectedEdge.data as EdgeData | undefined)?.condition || "",
                      label: e.target.value,
                    })
                  }
                />
              </label>
              <label className="block text-xs text-slate-500">
                Condition (optional, Python)
                <textarea
                  className="input mt-1 min-h-[100px] w-full font-mono text-xs"
                  value={(selectedEdge.data as EdgeData | undefined)?.condition || ""}
                  onChange={(e) =>
                    updateSelectedEdge({
                      condition: e.target.value,
                      label: (selectedEdge.data as EdgeData | undefined)?.label || "",
                    })
                  }
                  placeholder='e.g. "approved" in str(list(outputs.values())[-1])'
                />
              </label>
            </div>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn" onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save workflow"}
        </button>
        {onCancel && (
          <button type="button" className="text-sm text-slate-400 px-2" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
