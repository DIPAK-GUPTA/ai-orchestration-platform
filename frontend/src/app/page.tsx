import Link from "next/link";
import { Bot, GitBranch, Radio, BookTemplate } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-8 py-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Agent Orchestration Platform</h1>
        <p className="mt-1 max-w-2xl text-slate-400">
          Create agents with model, tools, memory, and guardrails, wire them in LangGraph workflows, and
          connect Telegram for human access. This UI drives the same APIs used by workers and the external
          channel.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/agents" className="card group block no-underline transition hover:border-blue-500/30">
          <div className="flex items-start gap-3">
            <Bot className="mt-0.5 h-6 w-6 text-blue-400" />
            <div>
              <h2 className="font-medium text-white">Agents</h2>
              <p className="text-sm text-slate-500">CRUD, tools, skills, memory, schedules, Telegram binding.</p>
            </div>
          </div>
        </Link>
        <Link href="/workflows" className="card group block no-underline transition hover:border-blue-500/30">
          <div className="flex items-start gap-3">
            <GitBranch className="mt-0.5 h-6 w-6 text-violet-400" />
            <div>
              <h2 className="font-medium text-white">Workflows</h2>
              <p className="text-sm text-slate-500">List graphs and list executions from the canvas.</p>
            </div>
          </div>
        </Link>
        <Link href="/executions" className="card group block no-underline transition hover:border-blue-500/30">
          <div className="flex items-start gap-3">
            <Radio className="mt-0.5 h-6 w-6 text-emerald-400" />
            <div>
              <h2 className="font-medium text-white">Live monitoring</h2>
              <p className="text-sm text-slate-500">Run workflows and watch WebSocket + logs per execution.</p>
            </div>
          </div>
        </Link>
        <Link href="/templates" className="card group block no-underline transition hover:border-blue-500/30">
          <div className="flex items-start gap-3">
            <BookTemplate className="mt-0.5 h-6 w-6 text-amber-400" />
            <div>
              <h2 className="font-medium text-white">Templates</h2>
              <p className="text-sm text-slate-500">At least two pre-built multi-agent patterns (3 in API).</p>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}
