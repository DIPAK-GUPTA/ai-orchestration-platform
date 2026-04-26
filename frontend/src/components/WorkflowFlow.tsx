"use client";

import { useCallback, useMemo } from "react";
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
import type { Workflow } from "@/lib/api";

function toFlow(wf: Workflow) {
  const nodes: Node[] = (wf.nodes || []).map((n) => ({
    id: n.id,
    position: { x: n.position_x || 0, y: n.position_y || 0 },
    data: { label: n.label || n.node_type },
    type: n.node_type === "start" || n.node_type === "end" ? "default" : "default",
  }));
  const edges: Edge[] = (wf.edges || []).map((e) => ({
    id: e.id,
    source: e.source_node_id,
    target: e.target_node_id,
    label: e.label || (e.condition ? "if" : undefined),
  }));
  return { nodes, edges };
}

type Props = { workflow: Workflow; readOnly?: boolean };

export function WorkflowFlow({ workflow, readOnly = true }: Props) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => toFlow(workflow),
    [workflow]
  );
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (p: Connection) => setEdges((e) => addEdge({ ...p, id: `e-${e.length}` }, e)),
    [setEdges]
  );

  return (
    <div className="h-[420px] w-full overflow-hidden rounded-lg border border-slate-800 bg-slate-950/50">
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={readOnly ? undefined : onConnect}
          nodesConnectable={!readOnly}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
