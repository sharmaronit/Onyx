import { edges, nodes, nodeById } from "@/lib/soc-data";

export function MiniMap({
  compromised = [],
  active,
  onSelect,
  height = 340,
}: {
  compromised?: string[];
  active?: string;
  onSelect?: (id: string) => void;
  height?: number;
}) {
  return (
    <div className="relative w-full bg-tile" style={{ height }}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        {edges.map(([a, b]) => {
          const na = nodeById(a);
          const nb = nodeById(b);
          const hot = compromised.includes(a) && compromised.includes(b);
          return (
            <line
              key={`${a}-${b}`}
              x1={na.x}
              y1={na.y}
              x2={nb.x}
              y2={nb.y}
              stroke={hot ? "var(--destructive)" : "var(--sidebar-border)"}
              strokeWidth={hot ? 0.55 : 0.25}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
      {nodes.map((n) => {
        const isHot = compromised.includes(n.id);
        const isActive = active === n.id;
        return (
          <button
            key={n.id}
            onClick={() => onSelect?.(n.id)}
            style={{ left: `${n.x}%`, top: `${n.y}%` }}
            className="absolute -translate-x-1/2 -translate-y-1/2 text-left"
          >
            <span
              className={`block h-3 w-3 rounded-full ring-2 transition-all ${
                isActive
                  ? "scale-[1.6] bg-destructive ring-destructive/40"
                  : isHot
                    ? "bg-destructive ring-destructive/25"
                    : n.critical
                      ? "bg-primary-on-dark ring-transparent"
                      : "bg-tile-muted ring-transparent"
              }`}
            />
            <span
              className={`mt-1 block whitespace-nowrap text-[10px] leading-none ${
                isHot ? "text-tile-foreground" : "text-tile-muted"
              }`}
            >
              {n.label}
            </span>
          </button>
        );
      })}
      <div className="absolute bottom-3 right-4 flex gap-4 text-[10px] text-tile-muted">
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-2 rounded-full bg-destructive" /> compromised
        </span>
        <span className="flex items-center gap-1.5">
          <i className="inline-block h-2 w-2 rounded-full bg-primary-on-dark" /> critical asset
        </span>
      </div>
    </div>
  );
}
