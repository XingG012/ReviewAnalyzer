/** 报告 & 数据查询 Hooks */

"use client";

import { useQuery } from "@tanstack/react-query";
import { getPersonas, getReport, getReviews, getTagged } from "@/lib/api-client";

export function useReport(taskId: string) {
  return useQuery({
    queryKey: ["tasks", taskId, "report"],
    queryFn: () => getReport(taskId),
    enabled: !!taskId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useReviews(
  taskId: string,
  filters?: { offset?: number; limit?: number; rating_min?: number; rating_max?: number },
) {
  return useQuery({
    queryKey: ["tasks", taskId, "reviews", filters],
    queryFn: () => getReviews(taskId, filters),
    enabled: !!taskId,
  });
}

export function useTagged(
  taskId: string,
  filters?: { tag_key?: string; tag_value?: string; offset?: number; limit?: number },
) {
  return useQuery({
    queryKey: ["tasks", taskId, "tagged", filters],
    queryFn: () => getTagged(taskId, filters),
    enabled: !!taskId,
  });
}

export function usePersonas(taskId: string) {
  return useQuery({
    queryKey: ["tasks", taskId, "personas"],
    queryFn: () => getPersonas(taskId),
    enabled: !!taskId,
    staleTime: 5 * 60 * 1000,
  });
}
