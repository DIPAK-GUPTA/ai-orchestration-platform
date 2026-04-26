"use client";

import useSWR from "swr";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type Agent } from "@/lib/api";

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useSWR<Agent>(id ? `/api/agents/${id}` : null, fetcher);

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (error || !data) return <p className="text-red-400">Not found</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">{data.name}</h1>
        <Link className="btn" href={`/agents/${id}/edit`}>
          Edit
        </Link>
      </div>
      <div className="card grid gap-3 sm:grid-cols-2 text-sm">
        <div>
          <h3 className="text-xs font-semibold uppercase text-slate-500">Role</h3>
          <p className="text-slate-200">{data.role}</p>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase text-slate-500">Model</h3>
          <p className="font-mono text-slate-200">{data.model}</p>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase text-slate-500">Status</h3>
          <p className="text-slate-200">{data.status}</p>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase text-slate-500">Telegram</h3>
          <p className="text-slate-200">
            {data.is_telegram_agent ? "Yes" : "No"} {data.telegram_chat_id && `· chat ${data.telegram_chat_id}`}
          </p>
        </div>
        <div className="sm:col-span-2">
          <h3 className="text-xs font-semibold uppercase text-slate-500">System prompt</h3>
          <p className="whitespace-pre-wrap text-slate-300">{data.system_prompt}</p>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase text-slate-500">Tools</h3>
          <p className="font-mono text-xs text-amber-200/90">{(data.tools || []).join(", ") || "—"}</p>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase text-slate-500">Skills</h3>
          <p className="text-sm text-cyan-200/90">{(data.skills || []).join(", ") || "—"}</p>
        </div>
        <div className="sm:col-span-2">
          <h3 className="text-xs font-semibold uppercase text-slate-500">Memory</h3>
          <pre className="mt-1 text-xs text-slate-400 overflow-x-auto max-w-full">
            {JSON.stringify(data.memory_config, null, 2)}
          </pre>
        </div>
        <div className="sm:col-span-2">
          <h3 className="text-xs font-semibold uppercase text-slate-500">Guardrails</h3>
          <pre className="mt-1 text-xs text-slate-400 overflow-x-auto max-w-full">
            {JSON.stringify(data.guardrails, null, 2)}
          </pre>
        </div>
        {data.schedule && (data.schedule as { enabled?: boolean }).enabled && (
          <div className="sm:col-span-2">
            <h3 className="text-xs font-semibold uppercase text-slate-500">Schedule</h3>
            <pre className="mt-1 text-xs text-slate-400 overflow-x-auto max-w-full">
              {JSON.stringify(data.schedule, null, 2)}
            </pre>
          </div>
        )}
        <div className="sm:col-span-2">
          <h3 className="text-xs font-semibold uppercase text-slate-500">Interaction rules</h3>
          <pre className="mt-1 text-xs text-slate-400 overflow-x-auto max-w-full">
            {JSON.stringify(data.interaction_rules, null, 2)}
          </pre>
        </div>
        <div className="sm:col-span-2">
          <h3 className="text-xs font-semibold uppercase text-slate-500">Channel config</h3>
          <pre className="mt-1 text-xs text-slate-400 overflow-x-auto max-w-full">
            {JSON.stringify(data.channel_config, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
