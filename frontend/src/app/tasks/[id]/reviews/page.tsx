/** 评论数据浏览页 */

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Container } from "@/components/layout/container";
import { useReviews } from "@/hooks/use-report";

export default function ReviewsPage() {
  const { id } = useParams<{ id: string }>();
  const [page, setPage] = useState(0);
  const [ratingMin, setRatingMin] = useState<number | undefined>();
  const pageSize = 20;

  const { data, isLoading } = useReviews(id, {
    offset: page * pageSize,
    limit: pageSize,
    rating_min: ratingMin,
  });

  if (isLoading) {
    return (
      <Container>
        <p className="text-muted-foreground">加载中...</p>
      </Container>
    );
  }

  return (
    <Container>
      <Link href={`/tasks/${id}`} className="text-sm text-muted-foreground hover:text-foreground">
        ← 返回任务详情
      </Link>
      <h1 className="text-2xl font-bold mt-2 mb-4">评论数据</h1>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        {[undefined, 4, 3, 2, 1].map((r) => (
          <button
            key={r ?? "all"}
            onClick={() => setRatingMin(r)}
            className={`rounded-full px-3 py-1 text-sm ${
              ratingMin === r ? "bg-primary text-primary-foreground" : "bg-muted"
            }`}
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
                  <th className="text-left p-3">评论内容</th>
                  <th className="text-left p-3 w-16">评分</th>
                  <th className="text-left p-3 w-24">作者</th>
                </tr>
              </thead>
              <tbody>
                {data.reviews.map((r) => (
                  <tr key={r.id} className="border-t">
                    <td className="p-3 max-w-md truncate">{r.body}</td>
                    <td className="p-3">{r.rating}★</td>
                    <td className="p-3 text-muted-foreground">{r.author}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex gap-2 mt-4 justify-center">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1 rounded border text-sm disabled:opacity-40"
            >
              上一页
            </button>
            <span className="px-3 py-1 text-sm text-muted-foreground">
              第 {page + 1} / {Math.ceil(data.total / pageSize)} 页
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={(page + 1) * pageSize >= data.total}
              className="px-3 py-1 rounded border text-sm disabled:opacity-40"
            >
              下一页
            </button>
          </div>
        </>
      )}
    </Container>
  );
}
