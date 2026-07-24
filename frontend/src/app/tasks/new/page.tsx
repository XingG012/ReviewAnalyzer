/** 创建新任务 — 选择数据源：CSV 上传 或 Sorftime ASIN */

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Container } from "@/components/layout/container";
import { CsvUploader } from "@/components/tasks/csv-uploader";
import { useCreateTask } from "@/hooks/use-tasks";
import type { DataSource, Site, UploadResponse } from "@/types";

const SITES: Site[] = ["US", "UK", "DE", "JP"];
const ASIN_RE = /^[A-Z0-9]{10}$/;

export default function NewTaskPage() {
  const router = useRouter();
  const createTask = useCreateTask();
  const [source, setSource] = useState<DataSource>("csv");
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [asin, setAsin] = useState("");
  const [site, setSite] = useState<Site>("US");
  const [maxReviews, setMaxReviews] = useState(500);
  const [errors, setErrors] = useState<string[]>([]);

  const handleSubmit = () => {
    const errs: string[] = [];
    // CSV mode: must have uploaded file
    if (source === "csv" && !uploadResult) {
      errs.push("请先上传 CSV 文件");
    }
    // Sorftime mode: must have valid ASIN
    if (source === "sorftime") {
      if (!asin) errs.push("请输入 ASIN");
      else if (!ASIN_RE.test(asin.toUpperCase()))
        errs.push("ASIN 格式不正确，应为 10 位字母数字组合");
    }
    // Config
    if (maxReviews < 10 || maxReviews > 2000) errs.push("评论数量应在 10-2000 之间");

    if (errs.length > 0) {
      setErrors(errs);
      return;
    }
    setErrors([]);

    const finalAsin = source === "csv" ? (asin || "CSV0000001").toUpperCase() : asin.toUpperCase();

    createTask.mutate(
      {
        asin: finalAsin,
        site,
        source,
        upload_id: source === "csv" ? uploadResult?.upload_id : undefined,
        config: { max_reviews: maxReviews, batch_size: 20, template: "premium-gold" },
      },
      {
        onSuccess: (task) => router.push(`/tasks/${task.id}`),
        onError: (err) => setErrors([err.message]),
      },
    );
  };

  return (
    <Container>
      <h1 className="text-2xl font-bold mb-6">新建分析任务</h1>

      {errors.length > 0 && (
        <div className="mb-4 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {errors.map((e, i) => (
            <p key={i}>{e}</p>
          ))}
        </div>
      )}

      <div className="max-w-md space-y-5">
        {/* Source toggle */}
        <div>
          <h2 className="text-sm font-semibold mb-2">数据来源</h2>
          <div className="flex rounded-lg border p-0.5 bg-muted">
            {[
              { key: "csv" as DataSource, label: "📁 CSV 文件上传" },
              { key: "sorftime" as DataSource, label: "🔗 Sorftime (ASIN)" },
            ].map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setSource(key)}
                className={`flex-1 rounded-md py-2 text-sm font-medium transition-colors ${
                  source === key
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* CSV: file upload */}
        {source === "csv" && (
          <div>
            <h2 className="text-sm font-semibold mb-2">上传 CSV 评论文件</h2>
            <CsvUploader
              onUploaded={(r) => setUploadResult(r)}
              onReset={() => setUploadResult(null)}
            />
          </div>
        )}

        {/* Sorftime: ASIN + Site */}
        {source === "sorftime" && (
          <div>
            <h2 className="text-sm font-semibold mb-2">商品信息</h2>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">ASIN</label>
                <input
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm font-mono"
                  placeholder="B0DGV4T6BK"
                  value={asin}
                  onChange={(e) => setAsin(e.target.value.toUpperCase())}
                  maxLength={10}
                />
              </div>
              <div>
                <label className="text-sm font-medium">站点</label>
                <select
                  className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                  value={site}
                  onChange={(e) => setSite(e.target.value as Site)}
                >
                  {SITES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Config (both modes) */}
        <div>
          <h2 className="text-sm font-semibold mb-2">分析配置</h2>
          <div>
            <label className="text-sm font-medium">评论数量上限: {maxReviews}</label>
            <input
              type="range"
              min={10}
              max={2000}
              step={10}
              className="mt-1 w-full"
              value={maxReviews}
              onChange={(e) => setMaxReviews(Number(e.target.value))}
            />
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={
            createTask.isPending ||
            (source === "csv" && !uploadResult) ||
            (source === "sorftime" && !asin)
          }
          className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {createTask.isPending ? "创建中..." : "开始分析"}
        </button>
      </div>
    </Container>
  );
}
