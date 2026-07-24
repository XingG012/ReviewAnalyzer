/** 任务详情页 */

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Container } from "@/components/layout/container";
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

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: task, isLoading } = useTask(id);
  const isActive = task && task.status !== "done" && task.status !== "failed";
  const { phase } = useSSE({ taskId: id, enabled: isActive });

  if (isLoading) {
    return (
      <Container>
        <p className="text-muted-foreground">加载中...</p>
      </Container>
    );
  }
  if (!task) {
    return (
      <Container>
        <p className="text-destructive">任务不存在</p>
      </Container>
    );
  }

  return (
    <Container>
      {/* Header */}
      <div className="mb-6">
        <Link href="/tasks" className="text-sm text-muted-foreground hover:text-foreground">
          ← 返回任务列表
        </Link>
        <div className="mt-2 flex items-center gap-3">
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
        <p className="mt-1 text-sm text-muted-foreground">
          创建于 {new Date(task.created_at).toLocaleString("zh-CN")}
          {task.completed_at && ` · 完成于 ${new Date(task.completed_at).toLocaleString("zh-CN")}`}
        </p>
      </div>

      {/* Progress (running tasks) */}
      {isActive && (
        <div className="mb-6 rounded-lg border p-4">
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-700"
              style={{ width: `${task.progress}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-sm text-muted-foreground">
            <span>{phase?.message ?? task.phase_message ?? "准备中..."}</span>
            <span>{task.progress}%</span>
          </div>
          <div className="mt-3 flex gap-2">
            {PHASES.map((name, i) => (
              <div
                key={name}
                className={`flex-1 text-center text-xs py-1 rounded ${
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

      {/* Results (done tasks) */}
      {task.status === "done" && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Link
            href={`/tasks/${id}/report`}
            className="rounded-lg border p-4 hover:shadow-md transition-shadow"
          >
            <h3 className="font-semibold">📄 洞察报告</h3>
            <p className="mt-1 text-sm text-muted-foreground">14 章 Markdown 报告全文</p>
          </Link>
          <Link
            href={`/tasks/${id}/reviews`}
            className="rounded-lg border p-4 hover:shadow-md transition-shadow"
          >
            <h3 className="font-semibold">📊 评论数据</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {task.total_reviews} 条评论 · {task.persona_count} 个画像
            </p>
          </Link>
          <Link
            href={`/export/${id}`}
            className="rounded-lg border p-4 hover:shadow-md transition-shadow"
          >
            <h3 className="font-semibold">⬇️ 文件导出</h3>
            <p className="mt-1 text-sm text-muted-foreground">CSV · Markdown · HTML</p>
          </Link>
        </div>
      )}

      {/* Failed */}
      {task.status === "failed" && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="font-medium text-destructive">分析失败</p>
          <p className="mt-1 text-sm text-muted-foreground">{task.error_message ?? "未知错误"}</p>
        </div>
      )}
    </Container>
  );
}
