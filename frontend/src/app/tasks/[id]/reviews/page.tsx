/** 评论数据浏览 — 统计卡片 + 评分筛选 + 分页表格 */

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Container } from "@/components/layout/container";
import { useReport, useReviews } from "@/hooks/use-report";
import { useTask } from "@/hooks/use-tasks";

export default function ReviewsPage() {
  const { id } = useParams<{ id: string }>();
  const [page, setPage] = useState(0);
  const [ratingMin, setRatingMin] = useState<number | undefined>();
  const pageSize = 20;

  const { data: task } = useTask(id);
  const { data: report } = useReport(id);
  const { data, isLoading } = useReviews(id, {
    offset: page * pageSize,
    limit: pageSize,
    rating_min: ratingMin,
  });
  const stats = report?.stats as Record<string, unknown> | null;
  const sentiment = stats?.sentiment as Record<string, number> | undefined;

  if (isLoading)
    return (
      <Container>
        <p className="text-muted-foreground">加载中...</p>
      </Container>
    );

  return (
    <Container>
      <Link href={`/tasks/${id}`} className="text-sm text-muted-foreground hover:text-foreground">
        ← 返回任务详情
      </Link>
      <h1 className="text-2xl font-bold mt-2 mb-4">评论数据</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "总评论数", value: data?.total ?? "-" },
          { label: "平均评分", value: task?.avg_rating?.toFixed(1) ?? "-" },
          { label: "积极", value: sentiment?.积极 ?? "-" },
          { label: "消极", value: sentiment?.消极 ?? "-" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border bg-card p-3 text-center">
            <p className="text-xl font-bold">{s.value}</p>
            <p className="text-xs text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        {[undefined, 5, 4, 3, 2, 1].map((r) => (
          <button
            type="button"
            key={r ?? "all"}
            onClick={() => {
              setRatingMin(r);
              setPage(0);
            }}
            className={`rounded-full px-3 py-1 text-sm ${ratingMin === r ? "bg-primary text-primary-foreground" : "bg-muted"}`}
          >
            {r === undefined ? "全部" : `≥${r}★`}
          </button>
        ))}
      </div>

      {/* Table */}
      {data && (
        <>
          <p className="text-sm text-muted-foreground mb-2">共 {data.total} 条评论</p>
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left p-3 w-[55%]">评论内容</th>
                  <th className="text-left p-3 w-[15%]">评分</th>
                  <th className="text-left p-3 w-[30%]">作者</th>
                </tr>
              </thead>
              <tbody>
                {data.reviews.map((r) => (
                  <tr key={r.id} className="border-t hover:bg-muted/30">
                    <td className="p-3 max-w-[300px] truncate">{r.body}</td>
                    <td className="p-3">
                      {"★".repeat(Math.round(r.rating))} {r.rating}
                    </td>
                    <td className="p-3 text-muted-foreground text-xs">{r.author ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2 mt-4 justify-center text-sm">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1 rounded border disabled:opacity-40"
            >
              上一页
            </button>
            <span className="px-3 py-1 text-muted-foreground">
              第 {page + 1} / {Math.ceil(data.total / pageSize)} 页
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => p + 1)}
              disabled={(page + 1) * pageSize >= data.total}
              className="px-3 py-1 rounded border disabled:opacity-40"
            >
              下一页
            </button>
          </div>
        </>
      )}
    </Container>
  );
}
