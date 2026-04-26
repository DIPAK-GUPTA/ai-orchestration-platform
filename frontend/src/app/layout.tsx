import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import { Activity } from "lucide-react";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "AI Agent Orchestration",
  description: "Configure agents, workflows, and external channels",
};

const nav = [
  { href: "/", label: "Home" },
  { href: "/agents", label: "Agents" },
  { href: "/workflows", label: "Workflows" },
  { href: "/executions", label: "Executions" },
  { href: "/messages", label: "Messages" },
  { href: "/templates", label: "Templates" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen">
        <header className="border-b border-slate-800/80 bg-slate-950/60 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-white no-underline">
              <Activity className="h-5 w-5 text-blue-400" />
              Orchestrator
            </Link>
            <nav className="flex flex-wrap gap-1 text-sm">
              {nav.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="rounded-md px-3 py-1.5 text-slate-300 no-underline hover:bg-slate-800 hover:text-white"
                >
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl p-4">{children}</main>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
