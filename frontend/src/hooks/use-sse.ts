/** SSE 实时进度 Hook */

"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import type { SSEProgressEvent, TaskResponse } from "@/types";

interface UseSSEOptions {
  taskId: string;
  enabled?: boolean;
}

export function useSSE({ taskId, enabled = true }: UseSSEOptions) {
  const [phase, setPhase] = useState<SSEProgressEvent | null>(null);
  const [done, setDone] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const qc = useQueryClient();

  const close = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!enabled || !taskId) return;

    const es = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"}/tasks/${taskId}/stream`,
    );
    eventSourceRef.current = es;

    es.addEventListener("progress", (e) => {
      try {
        const data = JSON.parse(e.data) as SSEProgressEvent;
        setPhase(data);
        // 更新 React Query 缓存中的 task progress
        qc.setQueryData<TaskResponse>(["tasks", taskId], (old) => {
          if (!old) return old;
          return { ...old, progress: data.progress, phase_message: data.message };
        });
      } catch {
        // ignore parse errors
      }
    });

    es.addEventListener("done", (e) => {
      try {
        JSON.parse(e.data);
        setDone(true);
        close();
        // 刷新任务数据
        qc.invalidateQueries({ queryKey: ["tasks", taskId] });
        qc.invalidateQueries({ queryKey: ["tasks"] });
      } catch {
        // ignore
      }
    });

    es.addEventListener("error", () => {
      close();
    });

    return () => {
      close();
    };
  }, [taskId, enabled, close, qc]);

  return { phase, done, close };
}
