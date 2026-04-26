"use client";

import { useRouter } from "next/navigation";
import { AgentForm } from "@/components/AgentForm";

export default function NewAgent() {
  const r = useRouter();
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">New agent</h1>
      <p className="text-sm text-slate-500">
        Configure name, model, memory, guardrails, schedules, interaction rules, and channel routing.
      </p>
      <AgentForm
        onSuccess={(id) => {
          r.push(`/agents/${id}`);
        }}
      />
    </div>
  );
}
