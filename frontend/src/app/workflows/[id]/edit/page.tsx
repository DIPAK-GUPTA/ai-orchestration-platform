"use client";

import { useParams, useRouter } from "next/navigation";
import { WorkflowGraphEditor } from "@/components/WorkflowGraphEditor";
import Link from "next/link";

export default function EditWorkflowPage() {
  const { id } = useParams<{ id: string }>();
  const r = useRouter();
  if (!id) return <p>Missing id</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Edit workflow</h1>
        <Link href={`/workflows/${id}`} className="text-sm text-slate-500 no-underline hover:text-slate-300">
          Open run view
        </Link>
      </div>
      <WorkflowGraphEditor
        workflowId={id}
        onSaved={() => {
          r.push(`/workflows/${id}`);
        }}
        onCancel={() => r.push(`/workflows/${id}`)}
      />
    </div>
  );
}
