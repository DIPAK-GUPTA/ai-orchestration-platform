"use client";

import { useParams, useRouter } from "next/navigation";
import { AgentForm } from "@/components/AgentForm";
import Link from "next/link";

export default function EditAgent() {
  const { id } = useParams<{ id: string }>();
  const r = useRouter();
  if (!id) return <p>Missing id</p>;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Edit agent</h1>
        <Link href={`/agents/${id}`} className="text-sm text-slate-500 no-underline hover:text-slate-300">
          View details
        </Link>
      </div>
      <AgentForm agentId={id} onSuccess={() => r.push(`/agents/${id}`)} onCancel={() => r.back()} />
    </div>
  );
}
