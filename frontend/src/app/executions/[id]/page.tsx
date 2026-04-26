"use client";

import useSWR from "swr";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Execution, wsBase } from "@/lib/api";

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function ExecutionDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useSWR<Execution>(id ? `/api/executions/${id}` : null, fetcher, {
    refreshInterval: 5000,
  });
  const [stream, setStream] = useState<string[]>([]);

  useEffect(() => {
    if (!id) return;
    const u = `${wsBase.replace(/^http/, "ws")}/ws/executions/${id}`;
    const ws = new WebSocket(u);
    ws.onmessage = (ev) => {
      try {
        const j = JSON.parse(ev.data) as {
          type?: string;
          log?: { level?: string; event?: string; message?: string };
          status?: string;
          from_agent_id?: string;
          to_agent_id?: string;
          message?: string;
        };
        if (j.type === "log" && j.log) {
          const lg = j.log;
          setStream((s) => [
            ...s.slice(-200),
            `[${lg.level ?? "—"}] ${lg.event ?? "—"}: ${lg.message ?? ""}`,
          ]);
        } else if (j.type === "a2a_message") {
          const a = (j.from_agent_id || "—").slice(0, 8);
          const t = (j.to_agent_id || "—").slice(0, 8);
          const p = (j.message || "").slice(0, 160);
          setStream((s) => [
            ...s.slice(-200),
            `[A2A] ${a} → ${t}: ${p}${(j.message && j.message.length > 160) ? "…" : ""}`,
          ]);
        } else if (j.type === "status_change") {
          setStream((s) => [...s, `Status: ${j.status ?? "?"}`]);
        }
      } catch {
        setStream((s) => [...s, String(ev.data)]);
      }
    };
    return () => ws.close();
  }, [id]);

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (error || !data) return <p className="text-red-400">Not found</p>;

  return (
    <div className="space-y-4">
      <h1 className="font-mono text-xl">Execution {data.id.slice(0, 8)}…</h1>
      <p className="text-slate-400">
        {data.status} · ~{data.total_tokens} tokens · cost ${(data.total_cost_usd || 0).toFixed(4)}
      </p>
      {data.error && <p className="text-red-400">Error: {data.error}</p>}
      {data.output_data && Object.keys(data.output_data).length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300">Output (per agent)</h2>
          <pre className="mt-2 max-h-64 overflow-auto text-xs text-slate-300">
            {JSON.stringify(data.output_data, null, 2)}
          </pre>
        </div>
      )}
      <div className="card">
        <h2 className="text-sm font-semibold text-slate-300">Server logs (REST)</h2>
        <ul className="mt-2 max-h-64 space-y-1 overflow-auto font-mono text-xs text-slate-400">
          {(data.logs || []).map((l) => (
            <li key={l.id}>
              [{l.level}] {l.event}: {l.message}
              {l.tokens_used ? ` · ${l.tokens_used} tok` : ""}
            </li>
          ))}
        </ul>
      </div>
      <div className="card">
        <h2 className="text-sm font-semibold text-slate-300">WebSocket stream</h2>
        <ul className="mt-2 max-h-48 space-y-0.5 overflow-auto font-mono text-[11px] text-emerald-200/80">
          {stream.length === 0 && <li className="text-slate-500">Waiting for events…</li>}
          {stream.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
