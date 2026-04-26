"use client";

import useSWR from "swr";
import Link from "next/link";
import { api, type Agent } from "@/lib/api";
import { Plus, MessageCircle } from "lucide-react";

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function AgentsPage() {
  const { data, error, isLoading } = useSWR<Agent[]>("/api/agents", fetcher);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Agents</h1>
          <p className="text-slate-400">Name, model, tools, memory, skills, and Telegram link.</p>
        </div>
        <Link href="/agents/new" className="btn no-underline">
          <Plus className="mr-1.5 h-4 w-4" /> New agent
        </Link>
      </div>
      {isLoading && <p className="text-slate-500">Loading…</p>}
      {error && <p className="text-red-400">Failed to load. Is the API up?</p>}
      {data && (
        <ul className="space-y-2">
          {data.length === 0 && <li className="text-slate-500">No agents yet.</li>}
          {data.map((a) => (
            <li key={a.id} className="card flex items-start justify-between gap-4">
              <div>
                <Link href={`/agents/${a.id}`} className="font-medium text-white no-underline">
                  {a.name}
                </Link>
                <p className="text-sm text-slate-500">{a.role}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Model: {a.model} · tools: {a.tools?.length ?? 0} · skills: {a.skills?.length ?? 0}
                </p>
                {a.is_telegram_agent && (
                  <p className="mt-1 flex items-center gap-1 text-xs text-cyan-400/90">
                    <MessageCircle className="h-3.5 w-3.5" />
                    Telegram enabled
                    {a.telegram_chat_id && ` (chat ${a.telegram_chat_id})`}
                  </p>
                )}
              </div>
              <span
                className="rounded border border-slate-600 px-2 py-0.5 text-xs uppercase text-slate-400"
              >
                {a.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
