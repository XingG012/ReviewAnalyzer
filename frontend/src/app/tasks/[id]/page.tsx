/** 任务详情页 — SSE 实时进度 + StatCards + Tab 切换 */

"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { DashboardView } from "@/components/dashboard/dashboard-view";
import { Container } from "@/components/layout/container";
import { usePersonas, useReport, useReviews } from "@/hooks/use-report";
import { useSSE } from "@/hooks/use-sse";
import { useTask } from "@/hooks/use-tasks";
import type { TaskStatus } from "@/types";

const PHASES = ["数据获取", "AI 打标", "用户画像", "洞察报告", "输出看板"];
const STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "等待中",
  fetching: "获取数据",
  tagging: "AI 打标",
  analyzing: "生成报告",
  rendering: "渲染看板",
  done: "已完成",
  failed: "失败",
};
type Tab = "dashboard" | "report" | "reviews";

function StatCards({ task }: { task: NonNullable<ReturnType<typeof useTask>["data"]> }) {
  const { data: report } = useReport(task.id);
  const { data: personas } = usePersonas(task.id);
  const stats = report?.stats as Record<string, unknown> | null;
  const sentiment = stats?.sentiment as Record<string, number> | undefined;
  const items = [
    { label: "总评论数", value: task.total_reviews },
    { label: "平均评分", value: task.avg_rating?.toFixed(1) ?? "-" },
    {
      label: "积极率",
      value:
        sentiment?.积极 && task.total_reviews > 0
          ? `${((sentiment.积极 / task.total_reviews) * 100).toFixed(0)}%`
          : "-",
    },
    { label: "画像数", value: (personas ?? []).length },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {items.map((s) => (
        <div key={s.label} className="rounded-lg border bg-card p-3 text-center">
          <p className="text-2xl font-bold">{s.value}</p>
          <p className="text-xs text-muted-foreground">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

function ReviewsInline({ taskId }: { taskId: string }) {
  const [page, setPage] = useState(0);
  const { data } = useReviews(taskId, { offset: page * 20, limit: 20 });
  if (!data) return <p className="text-muted-foreground text-sm">加载中...</p>;
  return (
    <div>
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3 w-[60%]">评论内容</th>
              <th className="text-left p-3">评分</th>
              <th className="text-left p-3">作者</th>
            </tr>
          </thead>
          <tbody>
            {data.reviews.map((r) => (
              <tr key={r.id} className="border-t hover:bg-muted/30">
                <td className="p-3 truncate max-w-[300px]">{r.body}</td>
                <td className="p-3">{r.rating}★</td>
                <td className="p-3 text-muted-foreground text-xs">{r.author}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2 mt-3 justify-center text-sm">
        <button
          type="button"
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="px-3 py-1 rounded border disabled:opacity-40"
        >
          上一页
        </button>
        <span className="px-3 py-1 text-muted-foreground">
          第 {page + 1} / {Math.ceil(data.total / 20)} 页
        </span>
        <button
          type="button"
          onClick={() => setPage((p) => p + 1)}
          disabled={(page + 1) * 20 >= data.total}
          className="px-3 py-1 rounded border disabled:opacity-40"
        >
          下一页
        </button>
      </div>
    </div>
  );
}

function DashboardTab({
  id,
  task,
}: {
  id: string;
  task: NonNullable<ReturnType<typeof useTask>["data"]>;
}) {
  const { data: report } = useReport(id);
  const { data: personas } = usePersonas(id);
  if (!report) return <p className="text-muted-foreground text-sm">加载看板...</p>;
  return <DashboardView task={task} report={report} personas={personas ?? []} />;
}

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const tab = (searchParams.get("tab") as Tab) ?? "dashboard";

  const { data: task, isLoading } = useTask(id);
  const isActive = task && task.status !== "done" && task.status !== "failed";
  const { phase, done } = useSSE({ taskId: id, enabled: isActive });

  // Auto-switch to dashboard when done
  if (done) {
    router.replace(`/tasks/${id}?tab=dashboard`);
  }

  if (isLoading)
    return (
      <Container>
        <p className="text-muted-foreground">加载中...</p>
      </Container>
    );
  if (!task)
    return (
      <Container>
        <p className="text-destructive">任务不存在</p>
      </Container>
    );

  return (
    <Container>
      <Link href="/tasks" className="text-sm text-muted-foreground hover:text-foreground">
        ← 返回任务列表
      </Link>
      <div className="mt-2 mb-1 flex items-center gap-3">
        <h1 className="text-2xl font-bold font-mono">{task.asin}</h1>
        <span
          className={`text-sm px-2 py-0.5 rounded ${
            isActive
              ? "bg-blue-100 text-blue-700"
              : task.status === "done"
                ? "bg-green-100 text-green-700"
                : "bg-red-100 text-red-700"
          }`}
        >
          {STATUS_LABELS[task.status as TaskStatus] ?? task.status}
        </span>
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        创建于 {new Date(task.created_at).toLocaleString("zh-CN")}
        {task.completed_at && ` · 完成于 ${new Date(task.completed_at).toLocaleString("zh-CN")}`}
      </p>

      {/* Progress (running) */}
      {isActive && (
        <div className="mb-6 rounded-lg border p-4">
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-700"
              style={{ width: `${phase?.progress ?? task.progress}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-sm text-muted-foreground">
            <span>{phase?.message ?? task.phase_message ?? "准备中..."}</span>
            <span>{phase?.progress ?? task.progress}%</span>
          </div>
          <div className="mt-3 flex gap-1">
            {PHASES.map((name, i) => (
              <div
                key={name}
                className={`flex-1 text-center text-[11px] py-1 rounded ${
                  i + 1 <= task.current_phase
                    ? "bg-primary/10 text-primary font-medium"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Failed */}
      {task.status === "failed" && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 mb-4">
          <p className="font-medium text-destructive">分析失败</p>
          <p className="mt-1 text-sm text-muted-foreground">{task.error_message ?? "未知错误"}</p>
        </div>
      )}

      {/* Done: StatCards + Tabs */}
      {task.status === "done" && (
        <>
          <StatCards task={task} />
          <div className="flex gap-1 mb-4 border-b">
            {[
              { key: "dashboard" as Tab, label: "看板" },
              { key: "report" as Tab, label: "报告" },
              { key: "reviews" as Tab, label: "评论数据" },
            ].map(({ key, label }) => (
              <Link
                key={key}
                href={`/tasks/${id}?tab=${key}`}
                className={`px-4 py-2 text-sm border-b-2 -mb-[1px] transition-colors ${
                  tab === key
                    ? "border-primary text-primary font-medium"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
          {tab === "dashboard" && <DashboardTab id={id} task={task} />}
          {tab === "report" && (
            <Link href={`/tasks/${id}/report`} className="text-sm text-primary hover:underline">
              → 全屏查看完整报告
            </Link>
          )}
          {tab === "reviews" && <ReviewsInline taskId={id} />}
        </>
      )}
    </Container>
  );
}
