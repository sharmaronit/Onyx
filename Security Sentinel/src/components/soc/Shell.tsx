import { Link, useRouterState } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import { Moon, Sun } from "lucide-react";
import { ROLES, useRole } from "@/lib/rbac";
import { useTheme } from "@/lib/theme";

const NAV: Array<{ to: string; label: string; hint: string }> = [
  { to: "/", label: "Executive Overview", hint: "Posture & risk" },
  { to: "/topology", label: "Asset Topology", hint: "Inventory & segments" },
  { to: "/exposure", label: "Exposure Analysis", hint: "Paths & findings" },
  { to: "/simulation", label: "Attack Simulation", hint: "Episode replay" },
  { to: "/patches", label: "Patch ROI", hint: "Prioritized actions" },
  { to: "/telemetry", label: "Telemetry", hint: "Live ingestion" },
];

export function Shell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const { role, setRole } = useRole();
  const { theme, toggle } = useTheme();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const current = NAV.find((n) => n.to === path);

  return (
    <div className="flex min-h-screen bg-background">
      <aside
        className={`sticky top-0 flex h-screen shrink-0 flex-col bg-sidebar text-sidebar-foreground transition-[width] duration-300 ${
          collapsed ? "w-[68px]" : "w-[248px]"
        }`}
      >
        <div className="flex h-11 items-center gap-2 border-b border-sidebar-border px-4">
          <span className="inline-block h-2 w-2 rounded-full bg-primary-on-dark" />
          {!collapsed && (
            <span className="font-display text-[13px] font-semibold tracking-tight">Sentinel Graph</span>
          )}
        </div>

        <nav className="flex-1 space-y-0.5 p-2 pt-3">
          {NAV.map((item) => {
            const active = item.to === path;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`block rounded-md px-3 py-2 transition-colors ${
                  active ? "bg-sidebar-accent" : "hover:bg-sidebar-accent/60"
                }`}
                title={item.label}
              >
                {collapsed ? (
                  <span className="block text-center text-[11px] font-semibold">
                    {item.label.slice(0, 2).toUpperCase()}
                  </span>
                ) : (
                  <>
                    <span className="block text-[13px] leading-tight">{item.label}</span>
                    <span className="block text-[11px] text-sidebar-muted">{item.hint}</span>
                  </>
                )}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={() => setCollapsed((c) => !c)}
          className="m-2 rounded-md px-3 py-2 text-left text-[12px] text-sidebar-muted hover:bg-sidebar-accent"
        >
          {collapsed ? "»" : "« Collapse sidebar"}
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-[52px] items-center justify-between gap-4 border-b border-hairline bg-card/85 px-6 backdrop-blur">
          <div className="min-w-0">
            <h1 className="truncate font-display text-[17px] font-semibold">
              {current?.label ?? "Console"}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden text-[12px] text-muted-foreground md:inline tabular">
              Last sync 21:44:08 UTC
            </span>
            <div className="flex items-center gap-1 rounded-full bg-pearl p-1">
              {ROLES.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setRole(r.id)}
                  className={`rounded-full px-3 py-1.5 text-[12px] transition-colors ${
                    role === r.id
                      ? "bg-primary text-primary-foreground"
                      : "text-secondary-foreground hover:text-foreground"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <button
              onClick={toggle}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              title={theme === "dark" ? "Light mode" : "Dark mode"}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-pearl text-secondary-foreground transition-colors hover:text-foreground"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>
        <main className="min-w-0 flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}

export function Metric({
  label,
  value,
  sub,
  tone = "ink",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "ink" | "primary" | "destructive" | "warning" | "success";
}) {
  const toneClass =
    tone === "primary"
      ? "text-primary"
      : tone === "destructive"
        ? "text-destructive"
        : tone === "warning"
          ? "text-warning"
          : tone === "success"
            ? "text-success"
            : "text-foreground";
  return (
    <div className="panel p-5">
      <p className="eyebrow">{label}</p>
      <p className={`mt-2 font-display text-[34px] font-semibold leading-none tabular ${toneClass}`}>
        {value}
      </p>
      {sub && <p className="mt-2 text-[12px] text-muted-foreground">{sub}</p>}
    </div>
  );
}

export function Panel({
  title,
  action,
  children,
  className = "",
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel overflow-hidden ${className}`}>
      <header className="flex items-center justify-between gap-3 border-b border-hairline px-5 py-3">
        <h2 className="font-display text-[14px] font-semibold">{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}

export function Locked({ children }: { children: string }) {
  return (
    <div className="rounded-md bg-pearl px-4 py-3 text-[13px] text-secondary-foreground">
      <span className="mr-2 rounded-sm bg-chip px-1.5 py-0.5 text-[11px] uppercase tracking-wide">
        Restricted
      </span>
      {children}
    </div>
  );
}
