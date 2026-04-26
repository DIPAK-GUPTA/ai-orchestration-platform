"use client";

import useSWR from "swr";
import Link from "next/link";
import { api, type Execution } from "@/lib/api";

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function ExecutionsPage() {
  const { data, isLoading, error } = useSWR<Execution[]>("/api/executions", fetcher);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Executions</h1>
      {isLoading && <p className="text-slate-500">Loading…</p>}
      {error && <p className="text-red-400">API error</p>}
      {data && (
        <ul className="space-y-2">
          {data.length === 0 && <li className="text-slate-500">No runs yet.</li>}
          {data.map((e) => (
            <li key={e.id} className="card">
              <Link href={`/executions/${e.id}`} className="font-mono text-sm text-blue-300 no-underline">
                {e.id}
              </Link>
              <p className="text-sm text-slate-400">
                {e.status} · tokens {e.total_tokens} · {e.trigger}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
