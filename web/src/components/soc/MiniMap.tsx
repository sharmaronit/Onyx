import { useMemo, useState, type PointerEvent as ReactPointerEvent } from "react";

export type MapNode = {
  node_id: string;
  node_type?: string;
  software?: string;
  version?: string;
  num_vulns?: number;
  max_cvss?: number;
  severity?: string;
  is_critical_asset?: boolean;
  is_entry_point?: boolean;
  hostname?: string;
  ip_address?: string | null;
  endpoint_status?: "active" | "offline" | "quarantined";
  security_state?: "healthy" | "warning" | "compromised" | "critical" | "quarantined" | "affected";
  x?: number;
  y?: number;
};

export type MapEdge = {
  source: string;
  target: string;
  connection_type?: string;
  permission_level?: string;
  has_firewall?: boolean;
};

export function MiniMap({
  nodes = [],
  edges = [],
  compromised = [],
  active,
  onSelect,
  height = 420,
  pathStepIds = [],
  layout = "auto",
}: {
  nodes?: MapNode[];
  edges?: MapEdge[];
  compromised?: string[];
  active?: string;
  onSelect?: (id: string) => void;
  height?: number;
  pathStepIds?: string[];
  layout?: "auto" | "circular";
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragOrigin, setDragOrigin] = useState({ x: 0, y: 0 });
  const adjustZoom = (delta: number) => {
    setZoom((value) => Math.min(1.8, Math.max(0.7, Number((value + delta).toFixed(2)))));
  };
  const layoutedNodes = useMemo(() => {
    if (nodes.length === 0) return [];

    if (layout === "circular") {
      const centerId = nodes.some((node) => node.node_id === "onyx_control_server")
        ? "onyx_control_server"
        : null;
      const ringNodes = centerId ? nodes.filter((node) => node.node_id !== centerId) : nodes;
      const radiusX = ringNodes.length <= 6 ? 34 : 38;
      const radiusY = ringNodes.length <= 6 ? 31 : 35;

      return nodes.map((node) => {
        if (node.node_id === centerId) return { ...node, x: 50, y: 46 };
        const index = ringNodes.findIndex((candidate) => candidate.node_id === node.node_id);
        const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(1, ringNodes.length);
        return {
          ...node,
          x: 50 + Math.cos(angle) * radiusX,
          y: 46 + Math.sin(angle) * radiusY,
        };
      });
    }

    const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
    const rows = Math.max(1, Math.ceil(nodes.length / columns));
    const xStep = columns === 1 ? 0 : 76 / (columns - 1);
    const yStep = rows === 1 ? 0 : 70 / (rows - 1);
    return nodes.map((n, i) => ({
      ...n,
      x: n.x ?? (columns === 1 ? 50 : 12 + (i % columns) * xStep),
      y: n.y ?? (rows === 1 ? 50 : 15 + Math.floor(i / columns) * yStep),
    }));
  }, [layout, nodes]);

  const nodeById = (id: string) => layoutedNodes.find((n) => n.node_id === id);

  const beginDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
    setDragOrigin({ x: event.clientX - pan.x, y: event.clientY - pan.y });
  };
  const moveDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragging) return;
    setPan({ x: event.clientX - dragOrigin.x, y: event.clientY - dragOrigin.y });
  };
  const endDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (dragging) event.currentTarget.releasePointerCapture?.(event.pointerId);
    setDragging(false);
  };

  return (
    <div className={`relative mx-auto w-full overflow-hidden rounded-md overscroll-contain ${dragging ? "cursor-grabbing" : "cursor-grab"}`} style={{ height: `${height}px`, aspectRatio: "16 / 9", backgroundColor: "var(--map-canvas)" }} onWheel={(event) => { event.preventDefault(); adjustZoom(event.deltaY > 0 ? -0.05 : 0.05); }} onPointerDown={beginDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag}>
      <div className="absolute right-3 top-3 z-10 flex overflow-hidden rounded-md border border-black/10 bg-white/90 shadow-sm dark:border-white/10 dark:bg-black/40" onPointerDown={(event) => event.stopPropagation()}>
        <button type="button" onClick={() => adjustZoom(0.1)} className="px-2.5 py-1 text-sm font-semibold text-foreground hover:bg-black/5 dark:hover:bg-white/10" aria-label="Zoom in">+</button>
        <span className="border-x border-black/10 px-2 py-1 text-[10px] tabular text-muted-foreground dark:border-white/10">{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={() => adjustZoom(-0.1)} className="px-2.5 py-1 text-sm font-semibold text-foreground hover:bg-black/5 dark:hover:bg-white/10" aria-label="Zoom out">−</button>
        <button type="button" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} className="border-l border-black/10 px-2 py-1 text-[10px] text-muted-foreground hover:bg-black/5 dark:border-white/10 dark:hover:bg-white/10" aria-label="Reset zoom">Reset</button>
      </div>
      <div className="absolute inset-0 transition-transform duration-150 ease-out" style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: "center" }}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 h-full w-full"
      >
        <defs>
          <marker id="onyx-arrow-hot" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse" markerUnits="strokeWidth">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--destructive)" />
          </marker>
          <marker id="onyx-arrow-neutral" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse" markerUnits="strokeWidth">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--secondary-foreground)" />
          </marker>
        </defs>
        {edges.map((edge, i) => {
          const a = edge.source;
          const b = edge.target;
          const na = nodeById(a);
          const nb = nodeById(b);
          if (!na || !nb) return null;
          const hot = compromised.includes(a) || compromised.includes(b);
          return (
            <line
              key={`${a}-${b}-${i}`}
              x1={na.x}
              y1={na.y}
              x2={nb.x}
              y2={nb.y}
              stroke={hot ? "var(--destructive)" : "var(--secondary-foreground)"}
              strokeOpacity={hot ? 0.9 : 0.42}
              strokeWidth={hot ? 0.85 : 0.6}
              markerEnd={`url(#${hot ? "onyx-arrow-hot" : "onyx-arrow-neutral"})`}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
      {layoutedNodes.map((n) => {
        const isHot = compromised.includes(n.node_id) || n.security_state === "compromised" || n.security_state === "affected";
        const isActive = active === n.node_id;
        const isCritical = n.is_critical_asset;
        const endpointState = n.endpoint_status as string | undefined;
        const warning = n.security_state === "warning";
        const compromisedState = n.security_state === "compromised";
        const criticalState = n.security_state === "critical";
        const pathStep = pathStepIds.indexOf(n.node_id) + 1;
        const endpointColor =
          endpointState === "quarantined"
            ? "bg-warning ring-warning/30"
            : criticalState
              ? "bg-primary ring-primary/30"
              : compromisedState
              ? "bg-destructive ring-destructive/30"
              : warning
                ? "bg-warning ring-warning/30"
            : endpointState === "active"
              ? "bg-success ring-success/30"
              : endpointState === "offline"
                ? "bg-secondary-foreground ring-transparent"
                : null;
        return (
          <button
            key={n.node_id}
            onClick={() => onSelect?.(n.node_id)}
            onPointerDown={(event) => event.stopPropagation()}
            aria-label={`Select ${n.node_id}`}
            style={{ left: `${n.x}%`, top: `${n.y}%` }}
            className="group absolute -translate-x-1/2 -translate-y-1/2 text-center"
          >
            <span
              className={`mx-auto block h-4 w-4 rounded-full border-2 border-[var(--map-canvas)] shadow-[0_2px_8px_rgba(0,0,0,0.24)] ring-2 transition-all ${
                `${endpointColor ? endpointColor : isHot ? "bg-destructive ring-destructive/25" : isCritical ? "bg-primary-on-dark ring-transparent" : "bg-secondary-foreground ring-transparent"} ${isActive ? "scale-[1.35] ring-4 ring-primary/40" : ""}`
              }`}
            />
            {pathStep > 0 && <span className="absolute -left-2 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-foreground px-1 text-[9px] font-bold text-background shadow-sm">{pathStep}</span>}
            <span
              className={`mt-1.5 block max-w-[150px] rounded-md bg-[var(--map-canvas)]/90 px-1.5 py-1 text-[11px] font-semibold leading-tight shadow-sm ${
                isHot ? "text-destructive" : "text-foreground"
              }`}
            >
              {n.node_id}
            </span>
          </button>
        );
      })}
      </div>
      <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 flex-wrap justify-center gap-3 rounded-full border border-black/5 bg-[var(--map-canvas)]/95 px-4 py-2 text-[10px] text-muted-foreground shadow-sm dark:border-white/10">
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-2 rounded-full bg-destructive" /> compromised
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-2 rounded-full bg-warning" /> warning
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-2 rounded-full bg-primary" /> critical
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-2 rounded-full bg-primary-on-dark" /> critical asset
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-2 rounded-full bg-success" /> live endpoint
        </span>
      </div>
    </div>
  );
}
