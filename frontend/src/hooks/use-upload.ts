/** CSV 上传 Hook */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getUploadHistory, uploadCSV } from "@/lib/api-client";

export function useUploadCSV() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadCSV(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["uploads"] });
    },
  });
}

export function useUploadHistory(limit = 20) {
  return useQuery({
    queryKey: ["uploads", { limit }],
    queryFn: () => getUploadHistory(limit),
  });
}
