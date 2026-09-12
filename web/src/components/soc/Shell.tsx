import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Bell,
  Moon,
  Sun,
  LayoutDashboard,
  Network,
  ShieldAlert,
  Crosshair,
  Wrench,
  Radio,
  UserCircle,
  Menu,
  X,
  ChevronDown,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ROLES, useRole, type Role } from "@/lib/rbac";
import { useTheme } from "@/lib/theme";
import { useAppMode } from "@/lib/app-mode";
import * as api from "@/lib/api";

const NAV: Array<{ to: string; label: string; hint: string; group: string; icon: LucideIcon }> = [
  {
    to: "/",
    label: "Executive Overview",
    hint: "Posture & risk",
    group: "Operations",
    icon: LayoutDashboard,
  },
  {
    to: "/topology",
    label: "Asset Topology",
    hint: "Inventory & segments",
    group: "Operations",
    icon: Network,
  },
  {
    to: "/telemetry",
    label: "Telemetry",
    hint: "Live ingestion",
    group: "Operations",
    icon: Radio,
  },
  {
    to: "/exposure",
    label: "Exposure Analysis",
    hint: "Paths & findings",
    group: "Analysis",
    icon: ShieldAlert,
  },
  {
    to: "/simulation",
    label: "Attack Simulation",
    hint: "Episode replay",
    group: "Analysis",
    icon: Crosshair,
  },
  {
    to: "/patches",
    label: "Patch ROI",
    hint: "Prioritized actions",
    group: "Analysis",
    icon: Wrench,
  },
];

function OnyxMark() {
  return (
    <span className="flex items-center gap-2.5">
      <svg className="h-8 w-8 shrink-0" viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <path
          d="M32 4 56 18v28L32 60 8 46V18L32 4Z"
          className="fill-neutral-950 dark:fill-neutral-100"
        />
        <path
          d="M32 12 49 22v20L32 52 15 42V22L32 12Z"
          className="fill-white dark:fill-neutral-900"
        />
        <path
          d="m22 34 13-10 2 19-15-9Zm13-10 0 0m2 19 0 0"
          className="stroke-neutral-800 dark:stroke-neutral-300"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="22" cy="34" r="5.4" className="fill-neutral-950 dark:fill-neutral-100" />
        <circle cx="35" cy="24" r="4.5" className="fill-neutral-600 dark:fill-neutral-400" />
        <circle cx="37" cy="43" r="4.5" className="fill-neutral-700 dark:fill-neutral-300" />
        <path
          d="m51 25 9 7-9 7"
          className="stroke-neutral-500 dark:stroke-neutral-400"
          strokeWidth="4"
          strokeLinecap="square"
          strokeLinejoin="miter"
        />
      </svg>
      <span className="onyx-wordmark text-[13px]">Onyx</span>
    </span>
  );
}

const ROLE_NAV: Record<Role, string[]> = {
  executive: ["/", "/exposure", "/patches"],
  architect: ["/", "/topology", "/telemetry", "/exposure", "/simulation", "/patches"],
  analyst: ["/", "/topology", "/telemetry", "/exposure", "/simulation"],
};

function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const seen = useRef<Set<string> | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: api.fetchNotifications,
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
    placeholderData: (previousData) => previousData,
  });
  const markAll = useMutation({
    mutationFn: api.markAllNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const clearAll = useMutation({
    mutationFn: api.clearAllNotifications,
    onSuccess: () => {
      toast.dismiss();
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      setOpen(false);
    },
  });
  const rows = useMemo(
    () => notifications.data?.notifications ?? [],
    [notifications.data?.notifications],
  );
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);
  useEffect(() => {
    const ids = new Set(rows.map((row) => row.notification_id));
    if (!seen.current) {
      seen.current = ids;
      return;
    }
    rows
      .filter((row) => !seen.current!.has(row.notification_id))
      .forEach((row) =>
        toast(row.title, { description: row.message, duration: 10000, id: row.notification_id }),
      );
    seen.current = ids;
  }, [rows]);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        className="relative flex h-9 w-9 items-center justify-center rounded-full bg-pearl text-secondary-foreground transition-all duration-200 hover:bg-white hover:text-foreground hover:shadow-sm dark:hover:bg-pearl"
        aria-label="Notifications"
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Bell className="h-4 w-4 transition-transform duration-200 group-hover:scale-105" />
        {(notifications.data?.unread_count ?? 0) > 0 && (
          <span className="absolute -right-1 -top-1 min-w-4 rounded-full bg-destructive px-1 text-[9px] text-white">
            {notifications.data!.unread_count}
          </span>
        )}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute right-0 top-11 z-50 w-[min(360px,calc(100vw-1rem))] animate-in fade-in slide-in-from-top-2 duration-200 overflow-hidden rounded-lg border border-hairline bg-card shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-hairline px-4 py-3">
            <span className="text-sm font-semibold">Notifications</span>
            <div className="flex gap-3">
              <button
                onClick={() => markAll.mutate()}
                className="text-[11px] text-primary transition-colors hover:text-foreground"
              >
                Mark all read
              </button>
              <button
                onClick={() => clearAll.mutate()}
                className="text-[11px] text-destructive transition-colors hover:text-foreground"
              >
                Clear all
              </button>
            </div>
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            {rows.length === 0 && (
              <p className="p-4 text-sm text-muted-foreground">No notifications yet.</p>
            )}
            {rows.map((row) => (
              <button
                key={row.notification_id}
                onClick={() => {
                  api
                    .markNotificationRead(row.notification_id)
                    .then(() => queryClient.invalidateQueries({ queryKey: ["notifications"] }));
                  if (row.endpoint_id) navigate({ to: "/telemetry" });
                  setOpen(false);
                }}
                className={`block w-full border-b border-hairline px-4 py-3 text-left transition-colors hover:bg-white dark:hover:bg-pearl ${!row.read_at ? "bg-primary/5" : ""}`}
              >
                <p
                  className={`text-xs font-semibold ${row.severity === "critical" ? "text-destructive" : "text-foreground"}`}
                >
                  {row.title}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">{row.message}</p>
                <p className="mt-1 text-[10px] text-muted-foreground">
                  {new Date(row.created_at).toLocaleString()}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { role, setRole } = useRole();
  const { theme, toggle } = useTheme();
  const { mode, setMode } = useAppMode();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const [openRole, setOpenRole] = useState<Role | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const shellRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    setOpenRole(null);
    setProfileOpen(false);
    setMobileOpen(false);
  }, [path]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenRole(null);
        setProfileOpen(false);
        setMobileOpen(false);
      }
    };
    const onPointerDown = (event: MouseEvent) => {
      if (shellRef.current && !shellRef.current.contains(event.target as Node)) {
        setOpenRole(null);
        setProfileOpen(false);
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, []);
  const selectedRole = openRole;
  const roleItems = selectedRole
    ? NAV.filter((item) => ROLE_NAV[selectedRole].includes(item.to))
    : [];
  const openMenuFor = (nextRole: Role) => {
    setOpenRole(nextRole);
    setProfileOpen(false);
  };
  const activateRole = (nextRole: Role) => {
    setRole(nextRole);
  };
  return (
    <div ref={shellRef} className="min-h-screen bg-background">
      <header className="onyx-nav-surface sticky top-0 z-40 border-b border-hairline">
        <div className="flex min-h-16 items-center gap-4 px-5 lg:px-8">
          <Link
            to="/"
            className="flex shrink-0 items-center rounded-md px-1 py-1 transition-colors hover:bg-white dark:hover:bg-pearl"
            aria-label="Onyx dashboard"
          >
            <OnyxMark />
          </Link>
          <nav
            aria-label="Role navigation"
            className="hidden min-w-0 flex-1 justify-center xl:flex"
          >
            <div className="flex items-center gap-1">
              {ROLES.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  aria-haspopup="menu"
                  aria-expanded={openRole === r.id}
                  onMouseEnter={() => openMenuFor(r.id)}
                  onFocus={() => openMenuFor(r.id)}
                  onClick={() => activateRole(r.id)}
                  className={`onyx-nav-label border-b-2 px-3 py-1.5 text-[12px] font-semibold transition-all duration-200 hover:text-foreground ${role === r.id || openRole === r.id ? "border-primary text-foreground" : "border-transparent text-secondary-foreground hover:border-primary"}`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <NotificationsBell />
            <div className="relative">
              <button
                type="button"
                aria-label="Profile menu"
                aria-haspopup="menu"
                aria-expanded={profileOpen}
                onClick={() => {
                  setProfileOpen((value) => !value);
                  setOpenRole(null);
                }}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-pearl text-secondary-foreground transition-all duration-200 hover:bg-white hover:text-foreground hover:shadow-sm dark:hover:bg-pearl"
              >
                <UserCircle className="h-4 w-4 transition-transform duration-200 hover:scale-105" />
              </button>
              {profileOpen && (
                <div
                  role="menu"
                  className="absolute right-0 top-11 z-50 w-52 animate-in fade-in slide-in-from-top-2 duration-200 rounded-lg border border-hairline bg-card p-2 shadow-xl"
                >
                  <p className="px-3 py-2 text-[11px] text-muted-foreground">
                    Current role:{" "}
                    <span className="font-medium text-foreground">
                      {ROLES.find((r) => r.id === role)?.label}
                    </span>
                  </p>
                  <div className="my-1 border-t border-hairline" />
                  <p className="px-3 pt-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                    Workspace mode
                  </p>
                  <div className="flex gap-1 p-2">
                    {(["reality", "demo"] as const).map((value) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setMode(value)}
                        className={`flex-1 rounded-md px-2 py-1.5 text-xs capitalize transition-colors ${mode === value ? "bg-primary text-primary-foreground" : "bg-pearl text-secondary-foreground hover:bg-white hover:text-foreground dark:hover:bg-pearl"}`}
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={toggle}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-xs text-secondary-foreground transition-colors hover:bg-white hover:text-foreground dark:hover:bg-pearl"
                  >
                    {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}{" "}
                    Switch to {theme === "dark" ? "light" : "dark"} theme
                  </button>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => setMobileOpen((value) => !value)}
              aria-label="Open navigation"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-pearl text-secondary-foreground transition-all duration-200 hover:bg-white hover:text-foreground hover:shadow-sm dark:hover:bg-pearl xl:hidden"
            >
              {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>
        {selectedRole && (
          <div
            onMouseEnter={() => setOpenRole(selectedRole)}
            onMouseLeave={() => setOpenRole(null)}
            className="onyx-nav-surface onyx-menu-enter absolute left-0 right-0 top-full hidden border-b border-hairline shadow-lg xl:block"
          >
            <div className="mx-auto grid max-w-[1100px] grid-cols-1 gap-1 px-5 py-4 sm:grid-cols-2 lg:grid-cols-3">
              {roleItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={() => {
                      setRole(selectedRole);
                      setOpenRole(null);
                    }}
                    className={`onyx-nav-label flex items-start gap-3 rounded-lg px-3 py-2.5 text-[12px] font-semibold transition-all duration-200 hover:text-foreground ${item.to === path ? "text-foreground" : "text-secondary-foreground"}`}
                  >
                    <Icon className="mt-0.5 h-4 w-4 text-primary" strokeWidth={1.8} />
                    <span>
                      <span className="onyx-nav-label block text-[12px] font-semibold">
                        {item.label}
                      </span>
                      <span className="block text-[11px] font-medium text-muted-foreground">
                        {item.hint}
                      </span>
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
        {mobileOpen && (
          <div className="animate-in fade-in slide-in-from-top-1 border-t border-hairline px-4 py-3 duration-200 xl:hidden">
            {ROLES.map((r) => (
              <div key={r.id} className="border-b border-hairline last:border-0">
                <button
                  type="button"
                  onClick={() => setOpenRole(openRole === r.id ? null : r.id)}
                  className="onyx-nav-label flex w-full items-center justify-between py-3 text-[12px] font-semibold transition-colors hover:text-foreground"
                >
                  {r.label}
                  <ChevronDown
                    className={`h-4 w-4 transition-transform duration-200 ${openRole === r.id ? "rotate-180" : ""}`}
                  />
                </button>
                {openRole === r.id && (
                  <div className="animate-in fade-in slide-in-from-top-1 grid gap-1 pb-3 duration-200">
                    {NAV.filter((item) => ROLE_NAV[r.id].includes(item.to)).map((item) => {
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.to}
                          to={item.to}
                          onClick={() => {
                            setRole(r.id);
                            setMobileOpen(false);
                            setOpenRole(null);
                          }}
                          className="onyx-nav-label flex items-center gap-3 rounded-md px-3 py-2 text-[12px] font-semibold transition-colors hover:text-foreground"
                        >
                          <Icon className="h-4 w-4 text-primary" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </header>
      <main className="min-w-0 px-5 py-6 lg:px-8">
        <div className="mx-auto w-full max-w-[1440px]">{children}</div>
      </main>
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
      <p
        className={`mt-2 font-display text-[34px] font-semibold leading-none tabular ${toneClass}`}
      >
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
