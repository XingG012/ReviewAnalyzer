/** TOP 标签柱状图 — Chart.js */

"use client";

import { BarElement, CategoryScale, Chart as ChartJS, LinearScale, Tooltip } from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

interface Props {
  labels: string[];
  values: number[];
  title?: string;
}

export function BarChart({ labels, values, title = "TOP 标签" }: Props) {
  const data = {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: "var(--accent)",
        borderRadius: 4,
        barThickness: 16,
      },
    ],
  };

  const options = {
    indexAxis: "y" as const,
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        ticks: { color: "var(--text-muted)", font: { size: 11 } },
        grid: { color: "var(--border)" },
      },
      y: { ticks: { color: "var(--text-dim)", font: { size: 11 } }, grid: { display: false } },
    },
  };

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="text-sm font-semibold mb-3">{title}</h3>
      <div className="h-[320px]">
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}
