/** 指标卡片行 — 4 个 KPI */

interface StatItem {
  label: string;
  value: string | number;
}

export function StatCards({ items }: { items: StatItem[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {items.map((s) => (
        <div key={s.label} className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold" style={{ fontFamily: "var(--font-mono)" }}>
            {s.value}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
        </div>
      ))}
    </div>
  );
}
