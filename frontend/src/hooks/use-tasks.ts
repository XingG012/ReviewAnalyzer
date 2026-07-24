/** 任务相关 TanStack Query Hooks */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createTask, deleteTask, getTask, listTasks, retryTask } from "@/lib/api-client";
import type { TaskCreate } from "@/types";

export function useTasks(filters?: { status?: string; offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => listTasks(filters),
    refetchInterval: (query) => {
      // 有未完成任务时每 5 秒轮询
      const data = query.state.data;
      if (!data) return false;
      return data.tasks.some((t) => t.status !== "done" && t.status !== "failed") ? 5000 : false;
    },
  });
}

export function useTask(id: string) {
  return useQuery({
    queryKey: ["tasks", id],
    queryFn: () => getTask(id),
    enabled: !!id,
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) => createTask(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTask(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useRetryTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => retryTask(id),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.setQueryData(["tasks", data.id], data);
    },
  });
}
