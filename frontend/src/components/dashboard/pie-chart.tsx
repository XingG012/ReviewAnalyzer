/** 情感分布饼图 — Chart.js */

"use client";

import { ArcElement, Chart as ChartJS, Legend, Tooltip } from "chart.js";
import { Pie } from "react-chartjs-2";

ChartJS.register(ArcElement, Tooltip, Legend);

interface Props {
  labels: string[];
  values: number[];
}

export function PieChart({ labels, values }: Props) {
  const colors = [
    "var(--chart-1)",
    "var(--chart-2)",
    "var(--chart-3)",
    "var(--chart-4)",
    "var(--chart-5)",
  ];

  const data = {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: colors.slice(0, labels.length),
        borderColor: "var(--bg)",
        borderWidth: 2,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { position: "bottom" as const, labels: { color: "var(--text-dim)", padding: 16 } },
    },
  };

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="text-sm font-semibold mb-3 text-center">情感分布</h3>
      <div className="max-w-[280px] mx-auto">
        <Pie data={data} options={options} />
      </div>
    </div>
  );
}
