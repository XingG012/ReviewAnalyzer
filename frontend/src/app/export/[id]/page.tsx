/** 文件导出下载页 */

"use client";

import { FileSpreadsheet, FileText, Globe } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Container } from "@/components/layout/container";
import { useTask } from "@/hooks/use-tasks";
import { getExportUrl } from "@/lib/api-client";

const formats = [
  {
    key: "csv" as const,
    icon: FileSpreadsheet,
    label: "CSV 打标数据",
    desc: "UTF-8 BOM，Excel 友好",
  },
  { key: "md" as const, icon: FileText, label: "Markdown 报告", desc: "14 章洞察报告全文" },
  { key: "html" as const, icon: Globe, label: "HTML 看板", desc: "自包含，离线可打开" },
];

export default function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const { data: task } = useTask(id);
  const isReady = task?.status === "done";

  return (
    <Container>
      <Link href={`/tasks/${id}`} className="text-sm text-muted-foreground hover:text-foreground">
        ← 返回任务详情
      </Link>
      <h1 className="text-2xl font-bold mt-2 mb-6">文件导出</h1>

      {!isReady && (
        <p className="text-muted-foreground mb-4">
          任务尚未完成，无法导出。当前状态: {task?.status ?? "加载中"}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        {formats.map(({ key, icon: Icon, label, desc }) => (
          <div
            key={key}
            className={`rounded-lg border p-6 ${
              isReady ? "hover:shadow-md transition-shadow" : "opacity-50"
            }`}
          >
            <Icon className="h-8 w-8 text-primary mb-3" />
            <h3 className="font-semibold">{label}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
            {isReady && (
              <a
                href={getExportUrl(id, key)}
                download
                className="mt-3 inline-block rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                下载
              </a>
            )}
          </div>
        ))}
      </div>
    </Container>
  );
}
