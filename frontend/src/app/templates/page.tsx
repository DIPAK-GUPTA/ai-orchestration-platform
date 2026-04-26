"use client";

import useSWR from "swr";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Library } from "lucide-react";

type Tpl = { id: string; name: string; description: string; category: string; icon: string };

const fetcher = (u: string) => api.get(u).then((r) => r.data);

export default function TemplatesPage() {
  const r = useRouter();
  const { data, isLoading, error } = useSWR<Tpl[]>("/api/templates", fetcher);

  async function useTemplate(id: string) {
    try {
      const res = await api.post(
        `/api/templates/${id}/instantiate`,
        null,
        { params: { name: `From template ${id}` } }
      );
      toast.success("Workflow created from template");
      r.push(`/workflows/${res.data.id}`);
    } catch {
      toast.error("Could not instantiate (check API / DB)");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Workflow templates</h1>
      <p className="text-slate-400">Pre-built multi-agent patterns. Instantiates agents + graph in one request.</p>
      {isLoading && <p className="text-slate-500">Loading…</p>}
      {error && <p className="text-red-400">API error</p>}
      {data && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {data.map((t) => (
            <li key={t.id} className="card flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Library className="h-4 w-4 text-amber-400" />
                  <h2 className="font-medium text-white">{t.name}</h2>
                </div>
                <p className="mt-1 text-sm text-slate-500">{t.description}</p>
                <p className="mt-2 text-xs text-slate-600">{t.category}</p>
              </div>
              <button type="button" className="btn mt-3 w-full sm:w-auto" onClick={() => useTemplate(t.id)}>
                Use template
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
