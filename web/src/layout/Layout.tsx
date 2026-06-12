import {
  Activity,
  Archive,
  Bot,
  CheckSquare,
  Cog,
  DatabaseBackup,
  FileText,
  FileSearch,
  GitBranch,
  GitCompare,
  LayoutDashboard,
  ListChecks,
  Play,
  Plug,
  UserRound
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useUiStore } from "../stores/uiStore";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/approvals", label: "Approvals", icon: CheckSquare },
  { to: "/evidence", label: "Evidence", icon: FileSearch },
  { to: "/workflows", label: "Workflows", icon: GitBranch },
  { to: "/runs", label: "Runs", icon: Activity },
  { to: "/runs/new", label: "Trigger", icon: Play },
  { to: "/shadows", label: "Shadows", icon: GitCompare },
  { to: "/learning", label: "Learning", icon: Bot },
  { to: "/autonomy", label: "Autonomy", icon: ListChecks },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/backup", label: "Backup", icon: DatabaseBackup },
  { to: "/scenarios", label: "Scenarios", icon: GitBranch },
  { to: "/config", label: "Config", icon: Cog },
  { to: "/agent-config", label: "Agent Config", icon: Bot },
  { to: "/adapters", label: "Adapters", icon: Plug },
  { to: "/external-agents", label: "External Agents", icon: Plug },
  { to: "/profile", label: "Profile", icon: UserRound },
  { to: "/archive", label: "Archive", icon: Archive, disabled: true }
];

export function Layout() {
  const token = useUiStore((state) => state.token);
  const setToken = useUiStore((state) => state.setToken);
  const health = useQuery({ queryKey: ["health", token], queryFn: getHealth, enabled: Boolean(token) });

  return (
    <div className="min-h-screen bg-[#eef2f7]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-border bg-white px-4 py-5 md:block">
        <div className="mb-6">
          <div className="text-lg font-semibold text-ink">Loop Harness</div>
          <div className="text-xs text-muted">Control Console</div>
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            if (item.disabled) {
              return (
                <span
                  key={item.to}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-400"
                  title="Archived scenarios are managed from the scenario list."
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </span>
              );
            }
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md px-3 py-2 text-sm ${
                    isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <div className="md:pl-64">
        <header className="sticky top-0 z-10 border-b border-border bg-white/95 px-4 py-3 backdrop-blur md:px-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <span className="md:hidden text-base font-semibold text-ink">Loop Harness</span>
              {token ? (
                <StatusBadge
                  value={health.data?.overall_status ?? (health.isError ? "unhealthy" : "checking")}
                />
              ) : (
                <StatusBadge value="token required" />
              )}
            </div>
            <label className="flex min-w-0 items-center gap-2 text-xs text-muted">
              API Token
              <input
                value={token}
                onChange={(event) => setToken(event.target.value)}
                className="h-9 w-full rounded-md border border-border bg-white px-3 text-sm text-ink outline-none focus:border-accent lg:w-96"
                placeholder="Bearer token from loopharness auth"
                type="password"
              />
            </label>
          </div>
        </header>
        <main className="px-4 py-6 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
