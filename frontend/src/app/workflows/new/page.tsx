"use client";

import { useRouter } from "next/navigation";
import { WorkflowGraphEditor } from "@/components/WorkflowGraphEditor";

export default function NewWorkflowPage() {
  const r = useRouter();
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">New workflow</h1>
      <WorkflowGraphEditor
        onSaved={(id) => {
          r.push(`/workflows/${id}`);
        }}
        onCancel={() => r.push("/workflows")}
      />
    </div>
  );
}
