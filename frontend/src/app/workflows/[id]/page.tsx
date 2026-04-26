"use client";

import { useState } from "react";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Workflow } from "@/lib/api";
import { Play } from "lucide-react";
import { toast } from "sonner";
import { WorkflowFlow } from "@/components/WorkflowFlow";

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function WorkflowDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data, isLoading, error } = useSWR<Workflow>(id ? `/api/workflows/${id}` : null, fetcher);
  const [topic, setTopic] = useState(
    "Research and summarize: the impact of renewable energy on European electricity prices in 2024."
  );

  async function run() {
    if (!id) return;
    const message = (topic || "").trim() || "Run the workflow with a clear, specific user request in one paragraph.";
    try {
      const res = await api.post("/api/executions", {
        workflow_id: id,
        input_data: { message },
        trigger: "manual",
      });
      toast.success("Execution started");
      router.push(`/executions/${res.data.id}`);
    } catch {
      toast.error("Failed to start");
    }
  }

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (error || !data) return <p className="text-red-400">Not found</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{data.name}</h1>
          <p className="text-slate-400">{data.description || "—"}</p>
        </div>
        {id && (
          <Link href={`/workflows/${id}/edit`} className="text-sm text-blue-300 no-underline hover:underline">
            Edit graph
          </Link>
        )}
        <div className="w-full min-w-[min(100%,22rem)] space-y-2 md:max-w-md">
          <label className="block text-xs text-slate-500">
            Input for the first agent (topic / task). This is sent as the user message to the graph.
            <textarea
              className="input mt-1 min-h-[88px] text-sm"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="E.g. Research: pros and cons of serverless for ML inference."
            />
          </label>
          <button type="button" className="btn" onClick={run}>
            <Play className="mr-1.5 h-4 w-4" /> Run workflow
          </button>
        </div>
      </div>
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-300">Visual graph</h2>
        <p className="text-xs text-slate-500">
          Drag to pan; scroll to zoom. Edges with conditions support routing decisions and feedback loops in
          the LangGraph runtime.
        </p>
        <WorkflowFlow workflow={data} readOnly={true} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h2 className="mb-2 text-sm font-semibold text-slate-300">Nodes</h2>
          <ul className="space-y-1 text-sm text-slate-400">
            {data.nodes.map((n) => (
              <li key={n.id} className="font-mono text-xs">
                {n.id} · {n.node_type} {n.label && `· ${n.label}`} {n.agent_id && `· agent ${n.agent_id.slice(0, 8)}…`}
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2 className="mb-2 text-sm font-semibold text-slate-300">Edges</h2>
          <ul className="space-y-1 text-sm text-slate-400">
            {data.edges.map((e) => (
              <li key={e.id} className="font-mono text-xs">
                {e.source_node_id} → {e.target_node_id}
                {e.condition && <span className="text-amber-200/80"> if {e.condition.slice(0, 40)}…</span>}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
