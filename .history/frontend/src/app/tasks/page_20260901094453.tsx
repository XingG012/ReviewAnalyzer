/** 任务仪表盘 — 主页面 */

"use client";

import { Plus, RotateCcw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Container } from "@/components/layout/container";
import { useCreateTask, useDeleteTask, useTasks } from "@/hooks/use-tasks";
import type { TaskResponse, TaskStatus } from "@/types";

const STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "等待中",
  fetching: "获取数据",
  tagging: "AI 打标",
  analyzing: "生成报告",
  rendering: "渲染看板",
  done: "已完成",
  failed: "失败",
};

const STATUS_ICONS: Record<TaskStatus, string> = {
  pending: "⏳",
  fetching: "📥",
  tagging: "🏷️",
  analyzing: "📊",
  rendering: "🎨",
  done: "✅",
  failed: "❌",
};

const FILTERS: Array<{ label: string; value: string | null }> = [
  { label: "全部", value: null },
  { label: "运行中", value: "running" },
  { label: "已完成", value: "done" },
  { label: "失败", value: "failed" },
];

function TaskCard({
  task,
  onDelete,
  onRetry,
}: {
  task: TaskResponse;
  onDelete: (id: string) => void;
  onRetry: (id: string) => void;
}) {
  const isActive = task.status !== "done" && task.status !== "failed";
  return (
    <div className="rounded-lg border p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between">
        <Link href={`/tasks/${task.id}`} className="flex-1">
          <div className="flex items-center gap-2">
            <span>{STATUS_ICONS[task.status as TaskStatus] ?? "❓"}</span>
            <span className="font-mono font-medium">{task.asin}</span>
            <span
              className={`text-xs px-1.5 py-0.5 rounded ${
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
          <div className="mt-1 text-sm text-muted-foreground">
            {task.total_reviews} 条评论 · {task.persona_count} 个画像
            {isActive && ` · 进度 ${task.progress}%`}
            {task.avg_rating && ` · 均分 ${task.avg_rating.toFixed(1)}`}
          </div>
        </Link>
        <div className="flex gap-1 ml-2">
          {task.status === "failed" && (
            <button
              onClick={() => onRetry(task.id)}
              className="p-1.5 rounded hover:bg-muted"
              title="重试"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={() => onDelete(task.id)}
            className="p-1.5 rounded hover:bg-muted text-destructive"
            title="删除"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      {isActive && (
        <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${task.progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

// 函数组件是房子，Hook是装在房子里的家具和电器。
// 没有Hook的函数组件只能做静态展示；调用了Hook之后，组件才有了状态、副作用、路由等 "活" 的能力。
export default function TasksPage() {
  const _router = useRouter();
  // 当前选中的任务状态筛选条件: 例如 "pending", "in_progress", "done", "failed"
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const { data, isLoading } = useTasks(statusFilter ? { status: statusFilter } : undefined);
  const createTask = useCreateTask();
  const deleteTask = useDeleteTask();

  return (
    <Container>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">分析任务</h1>
        <Link
          href="/tasks/new"
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          新建任务
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => setStatusFilter(f.value)}
            className={`rounded-full px-3 py-1 text-sm ${
              statusFilter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Task list */}
      {isLoading && <p className="text-muted-foreground">加载中...</p>}
      {data && data.tasks.length === 0 && (
        <p className="text-muted-foreground text-center py-12">
          暂无任务，点击「新建任务」开始分析
        </p>
      )}
      <div className="space-y-2">
        {data?.tasks.map((t) => (
          <TaskCard
            key={t.id}
            task={t}
            onDelete={(id) => {
              if (confirm("确定删除此任务？")) deleteTask.mutate(id);
            }}
            onRetry={(_id) => {
              createTask.mutate({ asin: t.asin, site: t.site as "US", source: t.source as "csv" });
            }}
          />
        ))}
      </div>
    </Container>
  );
}
