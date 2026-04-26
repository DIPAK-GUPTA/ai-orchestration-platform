"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

type Msg = {
  id: string;
  execution_id: string | null;
  agent_id: string | null;
  from_agent_id: string | null;
  to_agent_id: string | null;
  channel: string;
  role: string;
  content: string;
  message_metadata: Record<string, unknown>;
  created_at: string;
};

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function MessagesPage() {
  const { data, isLoading, error } = useSWR<Msg[]>("/api/messages?limit=100", fetcher, {
    refreshInterval: 10000,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Message history</h1>
      <p className="text-slate-400">Persisted channel and internal messages (from workflow + Telegram).</p>
      {isLoading && <p className="text-slate-500">Loading…</p>}
      {error && <p className="text-red-400">API error</p>}
      {data && (
        <ul className="space-y-2">
          {data.length === 0 && <li className="text-slate-500">No messages yet.</li>}
          {data.map((m) => (
            <li key={m.id} className="card text-sm">
              <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                <span className="rounded border border-slate-700 px-1.5 py-0.5 uppercase text-slate-400">
                  {m.channel}
                </span>
                <span>{m.role}</span>
                {m.from_agent_id && (
                  <span className="font-mono">from {m.from_agent_id.slice(0, 8)}…</span>
                )}
                {m.to_agent_id && (
                  <span className="font-mono text-emerald-300/80">to {m.to_agent_id.slice(0, 8)}…</span>
                )}
                {m.execution_id && (
                  <a
                    className="text-blue-300 no-underline hover:underline"
                    href={`/executions/${m.execution_id}`}
                  >
                    run {m.execution_id.slice(0, 8)}…
                  </a>
                )}
                <span className="font-mono text-slate-600">{m.created_at}</span>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-slate-200">{m.content}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
