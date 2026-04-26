"use client";

import useSWR from "swr";
import Link from "next/link";
import { api, type Workflow } from "@/lib/api";

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function WorkflowsPage() {
  const { data, error, isLoading } = useSWR<Workflow[]>("/api/workflows", fetcher);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Workflows</h1>
        <Link href="/workflows/new" className="btn no-underline">
          New workflow
        </Link>
      </div>
      <p className="text-slate-400">Graphs are built from nodes and edges; workers run them with LangGraph.</p>
      {isLoading && <p className="text-slate-500">Loading…</p>}
      {error && <p className="text-red-400">API error</p>}
      {data && (
        <ul className="space-y-2">
          {data.length === 0 && <li className="text-slate-500">No workflows. Instantiate a template first.</li>}
          {data.map((w) => (
            <li key={w.id} className="card">
              <Link href={`/workflows/${w.id}`} className="font-medium text-white no-underline">
                {w.name}
              </Link>
              <p className="text-sm text-slate-500">{w.description || "—"}</p>
              <p className="mt-1 text-xs text-slate-600">
                {w.nodes?.length ?? 0} nodes · {w.edges?.length ?? 0} edges · {w.status}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
