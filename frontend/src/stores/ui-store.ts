/** UI 状态管理 — 主题、侧边栏、Toast */

import { create } from "zustand";

export type ThemeId =
  | "premium-gold"
  | "dark-tech"
  | "linear-minimal"
  | "posthog-analytics"
  | "stripe-executive"
  | "warm-editorial";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: "default" | "destructive";
}

interface UIState {
  currentTheme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  dismissToast: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  currentTheme: "premium-gold",
  setTheme: (theme) => set({ currentTheme: theme }),
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toasts: [],
  addToast: (toast) =>
    set((s) => ({
      toasts: [...s.toasts, { ...toast, id: crypto.randomUUID() }],
    })),
  dismissToast: (id) =>
    set((s) => ({
      toasts: s.toasts.filter((t) => t.id !== id),
    })),
}));
