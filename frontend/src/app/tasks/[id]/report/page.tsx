/** 洞察报告全屏页 */

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Container } from "@/components/layout/container";
import { useReport } from "@/hooks/use-report";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const { data: report, isLoading } = useReport(id);

  if (isLoading) {
    return (
      <Container>
        <p className="text-muted-foreground">加载中...</p>
      </Container>
    );
  }
  if (!report?.insights_md) {
    return (
      <Container>
        <p className="text-destructive">报告不可用</p>
      </Container>
    );
  }

  return (
    <Container>
      <Link href={`/tasks/${id}`} className="text-sm text-muted-foreground hover:text-foreground">
        ← 返回任务详情
      </Link>
      <div className="mt-4 prose prose-neutral dark:prose-invert max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.insights_md}</ReactMarkdown>
      </div>
    </Container>
  );
}
