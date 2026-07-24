/** Dashboard 全貌 — 组装 StatCards + Charts + Personas */

"use client";

import type { PersonaResponse, ReportResponse, TaskResponse } from "@/types";
import { BarChart } from "./bar-chart";
import { PersonaCard } from "./persona-card";
import { PieChart } from "./pie-chart";
import { StatCards } from "./stat-cards";

interface Props {
  task: TaskResponse;
  report: ReportResponse;
  personas: PersonaResponse[];
}

export function DashboardView({ task, report, personas }: Props) {
  const stats = report.stats as Record<string, unknown> | null;
  const sentiment = stats?.sentiment as Record<string, number> | undefined;
  const topTags = stats?.top_tags as Record<string, number> | undefined;

  const statItems = [
    { label: "总评论数", value: task.total_reviews },
    { label: "平均评分", value: task.avg_rating?.toFixed(1) ?? "-" },
    {
      label: "积极率",
      value: sentiment?.积极 ? `${((sentiment.积极 / task.total_reviews) * 100).toFixed(0)}%` : "-",
    },
    { label: "画像数", value: personas.length },
  ];

  const pieLabels = sentiment ? Object.keys(sentiment) : [];
  const pieValues = sentiment ? Object.values(sentiment) : [];

  const top10 = topTags
    ? Object.entries(topTags)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
    : [];

  return (
    <div className="space-y-6">
      <StatCards items={statItems} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {pieLabels.length > 0 && <PieChart labels={pieLabels} values={pieValues} />}
        {top10.length > 0 && (
          <BarChart labels={top10.map(([k]) => k)} values={top10.map(([, v]) => v)} />
        )}
      </div>

      {personas.length > 0 && (
        <div>
          <h3 className="font-semibold text-lg mb-3">用户画像</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {personas.map((p) => (
              <PersonaCard key={p.id} persona={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
