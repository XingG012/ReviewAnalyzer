/** 新建任务草稿 — 在页面间切换时保留表单状态 */

import { create } from "zustand";
import type { DataSource, Site } from "@/types";

interface TaskDraft {
  asin: string;
  site: Site;
  source: DataSource;
  uploadId: string | null;
  config: {
    max_reviews: number;
    batch_size: number;
    template: string;
  };
}

interface TaskDraftState {
  draft: TaskDraft;
  setDraft: (partial: Partial<TaskDraft>) => void;
  resetDraft: () => void;
}

const defaultDraft: TaskDraft = {
  asin: "",
  site: "US",
  source: "csv",
  uploadId: null,
  config: {
    max_reviews: 500,
    batch_size: 20,
    template: "premium-gold",
  },
};

export const useTaskDraftStore = create<TaskDraftState>((set) => ({
  draft: { ...defaultDraft },
  setDraft: (partial) => set((s) => ({ draft: { ...s.draft, ...partial } })),
  resetDraft: () => set({ draft: { ...defaultDraft } }),
}));
