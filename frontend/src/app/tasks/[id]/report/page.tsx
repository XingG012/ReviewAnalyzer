/** 洞察报告全屏 — 悬浮 TOC 导航 + Markdown 渲染 */

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Container } from "@/components/layout/container";
import { useReport } from "@/hooks/use-report";

function extractTOC(md: string): { id: string; title: string; level: number }[] {
  const headings: { id: string; title: string; level: number }[] = [];
  for (const line of md.split("\n")) {
    const m = line.match(/^(#{1,4})\s+(.+)/);
    if (m) {
      const level = m[1].length;
      const title = m[2].replace(/[#*`]/g, "").trim();
      headings.push({ id: `h-${title}`, title, level });
    }
  }
  return headings;
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const { data: report, isLoading } = useReport(id);
  const toc = useMemo(() => (report?.insights_md ? extractTOC(report.insights_md) : []), [report]);

  if (isLoading)
    return (
      <Container>
        <p className="text-muted-foreground">加载中...</p>
      </Container>
    );
  if (!report?.insights_md)
    return (
      <Container>
        <p className="text-destructive">报告不可用</p>
      </Container>
    );

  return (
    <Container>
      <Link href={`/tasks/${id}`} className="text-sm text-muted-foreground hover:text-foreground">
        ← 返回任务详情
      </Link>
      <div className="mt-4 flex gap-6">
        {/* TOC sidebar */}
        {toc.length > 0 && (
          <nav className="hidden lg:block w-52 shrink-0">
            <div className="sticky top-6">
              <h3 className="text-sm font-semibold mb-2">目录</h3>
              <ul className="space-y-1">
                {toc.map((h) => (
                  <li key={h.id} style={{ paddingLeft: `${(h.level - 1) * 12}px` }}>
                    <a
                      href={`#${h.id}`}
                      className="text-xs text-muted-foreground hover:text-foreground block py-0.5 transition-colors"
                    >
                      {h.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </nav>
        )}
        {/* Content */}
        <div className="flex-1 min-w-0 prose prose-neutral dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.insights_md}</ReactMarkdown>
        </div>
      </div>
    </Container>
  );
}
