/** 创建新任务 */

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Container } from "@/components/layout/container";
import { useCreateTask } from "@/hooks/use-tasks";
import { type TaskCreateForm, taskCreateSchema } from "@/lib/validators";
import type { Site } from "@/types";

const SITES: Site[] = ["US", "UK", "DE", "JP"];

export default function NewTaskPage() {
  const router = useRouter();
  const createTask = useCreateTask();
  const [form, setForm] = useState<TaskCreateForm>({
    asin: "",
    site: "US",
    source: "csv",
    config: { max_reviews: 500, batch_size: 20, template: "premium-gold" },
  });
  const [errors, setErrors] = useState<string[]>([]);

  const handleSubmit = () => {
    const result = taskCreateSchema.safeParse(form);
    if (!result.success) {
      setErrors(result.error.issues.map((i) => i.message));
      return;
    }
    setErrors([]);
    createTask.mutate(
      {
        asin: form.asin.toUpperCase(),
        site: form.site,
        source: form.source,
        config: form.config,
      },
      {
        onSuccess: (data) => {
          router.push(`/tasks/${data.id}`);
        },
        onError: (err) => {
          setErrors([err.message]);
        },
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

      <div className="max-w-md space-y-4">
        {/* ASIN */}
        <div>
          <label className="text-sm font-medium">ASIN</label>
          <input
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="B0DGV4T6BK"
            value={form.asin}
            onChange={(e) => setForm({ ...form, asin: e.target.value.toUpperCase() })}
            maxLength={10}
          />
        </div>

        {/* Site */}
        <div>
          <label className="text-sm font-medium">站点</label>
          <select
            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
            value={form.site}
            onChange={(e) => setForm({ ...form, site: e.target.value as Site })}
          >
            {SITES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {/* Max reviews */}
        <div>
          <label className="text-sm font-medium">评论数量上限: {form.config.max_reviews}</label>
          <input
            type="range"
            min={10}
            max={2000}
            step={10}
            className="mt-1 w-full"
            value={form.config.max_reviews}
            onChange={(e) =>
              setForm({
                ...form,
                config: { ...form.config, max_reviews: Number(e.target.value) },
              })
            }
          />
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={createTask.isPending}
          className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {createTask.isPending ? "创建中..." : "开始分析"}
        </button>
      </div>
    </Container>
  );
}
