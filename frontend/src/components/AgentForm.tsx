"use client";

import { useEffect, useState } from "react";
import { api, type Agent } from "@/lib/api";
import { toast } from "sonner";

const DEFAULT = {
  name: "Researcher",
  role: "Analyst",
  system_prompt: "You are a helpful, precise assistant. Follow the user and use tools when useful.",
  model: "gpt-4o-mini",
  tools: "web_search,get_datetime",
  skills: "data_analysis, report_writing",
  is_telegram_agent: false,
  telegram_chat_id: "",
  memoryType: "buffer" as "buffer" | "summary",
  maxTokens: 4096,
  memoryPersist: true,
  gMaxTokensPerTurn: 2000,
  gMaxTurns: 50,
  gAllowed: "",
  gBlocked: "",
  gRate: 0,
  schedEnabled: false,
  schedCron: "0 9 * * 1-5",
  schedTz: "UTC",
  schedPrompt: "Run your scheduled check-in.",
  interactionJson: "{\n  \"tone\": \"professional\"\n}",
  channelJson: "{}",
};

type Props = {
  agentId?: string;
  onSuccess?: (id: string) => void;
  onCancel?: () => void;
};

function fromAgent(a: Agent) {
  const m = a.memory_config || {};
  const g = a.guardrails || {};
  const s = a.schedule || {};
  return {
    name: a.name,
    role: a.role,
    system_prompt: a.system_prompt,
    model: a.model,
    tools: (a.tools || []).join(", "),
    skills: (a.skills || []).join(", "),
    is_telegram_agent: a.is_telegram_agent,
    telegram_chat_id: a.telegram_chat_id || "",
    memoryType: m.type === "summary" ? ("summary" as const) : ("buffer" as const),
    maxTokens: Number(m.max_tokens ?? 4096),
    memoryPersist: m.persist !== false,
    gMaxTokensPerTurn: Number((g as { max_tokens_per_turn?: number }).max_tokens_per_turn ?? 2000),
    gMaxTurns: Number((g as { max_turns?: number }).max_turns ?? 50),
    gAllowed: ((g as { allowed_topics?: string[] }).allowed_topics || []).join(", "),
    gBlocked: ((g as { blocked_topics?: string[] }).blocked_topics || []).join(", "),
    gRate: Number((g as { rate_limit_per_minute?: number }).rate_limit_per_minute ?? 0),
    schedEnabled: !!(s as { enabled?: boolean }).enabled,
    schedCron: (s as { cron?: string }).cron || "0 9 * * 1-5",
    schedTz: (s as { timezone?: string }).timezone || "UTC",
    schedPrompt: (s as { trigger_prompt?: string }).trigger_prompt || "Run your scheduled check-in.",
    interactionJson: JSON.stringify(a.interaction_rules || { tone: "professional" }, null, 2),
    channelJson: JSON.stringify(a.channel_config || {}, null, 2),
  };
}

export function AgentForm({ agentId, onSuccess, onCancel }: Props) {
  const [f, setF] = useState(DEFAULT);
  const [saving, setSaving] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  useEffect(() => {
    if (!agentId) {
      setF(DEFAULT);
      return;
    }
    (async () => {
      try {
        const { data: a } = await api.get<Agent>(`/api/agents/${agentId}`);
        setF(fromAgent(a));
        setLoadErr(null);
      } catch {
        setLoadErr("Not found");
      }
    })();
  }, [agentId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    let inter: Record<string, unknown> = {};
    let ch: Record<string, unknown> = {};
    try {
      inter = JSON.parse(f.interactionJson || "{}");
    } catch {
      toast.error("Interaction rules must be valid JSON");
      return;
    }
    try {
      ch = JSON.parse(f.channelJson || "{}");
    } catch {
      toast.error("Channel config must be valid JSON");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: f.name,
        role: f.role,
        system_prompt: f.system_prompt,
        model: f.model,
        tools: f.tools
          .split(/[, ]+/)
          .map((s) => s.trim())
          .filter(Boolean),
        skills: f.skills
          .split(/[, ]+/)
          .map((s) => s.trim())
          .filter(Boolean),
        is_telegram_agent: f.is_telegram_agent,
        telegram_chat_id: f.telegram_chat_id || null,
        memory_config: {
          type: f.memoryType,
          max_tokens: f.maxTokens,
          persist: f.memoryPersist,
        },
        guardrails: {
          max_tokens_per_turn: f.gMaxTokensPerTurn,
          max_turns: f.gMaxTurns,
          allowed_topics: f.gAllowed
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          blocked_topics: f.gBlocked
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          rate_limit_per_minute: f.gRate,
        },
        schedule: f.schedEnabled
          ? {
              enabled: true,
              cron: f.schedCron,
              timezone: f.schedTz,
              trigger_prompt: f.schedPrompt,
            }
          : null,
        interaction_rules: inter,
        channel_config: ch,
      };
      if (agentId) {
        await api.patch(`/api/agents/${agentId}`, payload);
        toast.success("Agent updated");
        onSuccess?.(agentId);
      } else {
        const res = await api.post<Agent>("/api/agents", payload);
        toast.success("Agent created");
        onSuccess?.(res.data.id);
      }
    } catch (e: unknown) {
      const msg = e && typeof e === "object" && "message" in e ? String((e as { message: string }).message) : "Error";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }

  if (loadErr) return <p className="text-red-400">{loadErr}</p>;

  return (
    <form onSubmit={onSubmit} className="space-y-6 max-w-2xl">
      <h2 className="text-lg font-semibold text-slate-200">Core</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm text-slate-300">
          Name
          <input
            className="input mt-1"
            value={f.name}
            onChange={(e) => setF({ ...f, name: e.target.value })}
            required
          />
        </label>
        <label className="block text-sm text-slate-300">
          Role
          <input className="input mt-1" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} required />
        </label>
        <label className="block text-sm text-slate-300 sm:col-span-2">
          Model
          <input className="input mt-1 font-mono" value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })} />
        </label>
        <label className="block text-sm text-slate-300 sm:col-span-2">
          System prompt
          <textarea
            className="input mt-1 min-h-[120px] font-mono"
            value={f.system_prompt}
            onChange={(e) => setF({ ...f, system_prompt: e.target.value })}
            required
          />
        </label>
        <label className="block text-sm text-slate-300 sm:col-span-2">
          Tools (comma-separated)
          <input
            className="input mt-1 font-mono"
            value={f.tools}
            onChange={(e) => setF({ ...f, tools: e.target.value })}
            placeholder="web_search,send_agent_message,…"
          />
        </label>
        <label className="block text-sm text-slate-300 sm:col-span-2">
          Skills (labels, comma-separated)
          <input
            className="input mt-1"
            value={f.skills}
            onChange={(e) => setF({ ...f, skills: e.target.value })}
          />
        </label>
      </div>

      <h2 className="text-lg font-semibold text-slate-200">Memory</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm text-slate-300">
          Type
          <select
            className="input mt-1"
            value={f.memoryType}
            onChange={(e) => setF({ ...f, memoryType: e.target.value as typeof f.memoryType })}
          >
            <option value="buffer">buffer</option>
            <option value="summary">summary</option>
          </select>
        </label>
        <label className="block text-sm text-slate-300">
          Max tokens
          <input
            type="number"
            className="input mt-1"
            value={f.maxTokens}
            onChange={(e) => setF({ ...f, maxTokens: parseInt(e.target.value, 10) || 4096 })}
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-300 sm:col-span-2">
          <input
            type="checkbox"
            checked={f.memoryPersist}
            onChange={(e) => setF({ ...f, memoryPersist: e.target.checked })}
          />
          Persist memory in Redis
        </label>
      </div>

      <h2 className="text-lg font-semibold text-slate-200">Guardrails</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm text-slate-300">
          Max tokens / turn
          <input
            type="number"
            className="input mt-1"
            value={f.gMaxTokensPerTurn}
            onChange={(e) => setF({ ...f, gMaxTokensPerTurn: parseInt(e.target.value, 10) || 2000 })}
          />
        </label>
        <label className="block text-sm text-slate-300">
          Max turns (per agent in graph)
          <input
            type="number"
            className="input mt-1"
            value={f.gMaxTurns}
            onChange={(e) => setF({ ...f, gMaxTurns: parseInt(e.target.value, 10) || 50 })}
          />
        </label>
        <label className="block text-sm text-slate-300 sm:col-span-2">
          Allowed topics (comma keywords; if set, at least one must match user text)
          <input
            className="input mt-1"
            value={f.gAllowed}
            onChange={(e) => setF({ ...f, gAllowed: e.target.value })}
            placeholder="billing, support"
          />
        </label>
        <label className="block text-sm text-slate-300 sm:col-span-2">
          Blocked topics (comma substrings)
          <input
            className="input mt-1"
            value={f.gBlocked}
            onChange={(e) => setF({ ...f, gBlocked: e.target.value })}
          />
        </label>
        <label className="block text-sm text-slate-300 sm:col-span-2">
          Rate limit (requests / min per agent, 0 = off)
          <input
            type="number"
            className="input mt-1"
            value={f.gRate}
            onChange={(e) => setF({ ...f, gRate: parseInt(e.target.value, 10) || 0 })}
          />
        </label>
      </div>

      <h2 className="text-lg font-semibold text-slate-200">Schedule (Celery beat)</h2>
      <label className="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={f.schedEnabled}
          onChange={(e) => setF({ ...f, schedEnabled: e.target.checked })}
        />
        Enable scheduled runs
      </label>
      {f.schedEnabled && (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm text-slate-300 sm:col-span-2">
            Cron
            <input
              className="input mt-1 font-mono"
              value={f.schedCron}
              onChange={(e) => setF({ ...f, schedCron: e.target.value })}
            />
          </label>
          <label className="block text-sm text-slate-300">
            Timezone
            <input
              className="input mt-1"
              value={f.schedTz}
              onChange={(e) => setF({ ...f, schedTz: e.target.value })}
            />
          </label>
          <label className="block text-sm text-slate-300 sm:col-span-2">
            Trigger prompt
            <input
              className="input mt-1"
              value={f.schedPrompt}
              onChange={(e) => setF({ ...f, schedPrompt: e.target.value })}
            />
          </label>
        </div>
      )}

      <h2 className="text-lg font-semibold text-slate-200">Interaction & channels</h2>
      <label className="block text-sm text-slate-300">
        Interaction rules (JSON, merged into system context)
        <textarea
          className="input mt-1 min-h-[100px] font-mono text-sm"
          value={f.interactionJson}
          onChange={(e) => setF({ ...f, interactionJson: e.target.value })}
        />
      </label>
      <label className="block text-sm text-slate-300">
        Channel config (JSON, extensions for Slack/WhatsApp, etc.)
        <textarea
          className="input mt-1 min-h-[80px] font-mono text-sm"
          value={f.channelJson}
          onChange={(e) => setF({ ...f, channelJson: e.target.value })}
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={f.is_telegram_agent}
          onChange={(e) => setF({ ...f, is_telegram_agent: e.target.checked })}
        />
        Expose on Telegram
      </label>
      {f.is_telegram_agent && (
        <label className="block text-sm text-slate-300">
          Telegram chat id (optional, bound after first message)
          <input
            className="input mt-1 font-mono"
            value={f.telegram_chat_id}
            onChange={(e) => setF({ ...f, telegram_chat_id: e.target.value })}
            placeholder="123456789"
          />
        </label>
      )}

      <div className="flex flex-wrap gap-2">
        <button type="submit" className="btn" disabled={saving}>
          {saving ? "Saving…" : agentId ? "Save" : "Create agent"}
        </button>
        {onCancel && (
          <button type="button" className="text-sm text-slate-400" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
