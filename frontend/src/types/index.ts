/** 共享 TypeScript 类型定义 — 与后端 Pydantic Schema 对齐 */

// ── 枚举 ─────────────────────────────────────────────────

export type TaskStatus =
  | "pending"
  | "fetching"
  | "tagging"
  | "analyzing"
  | "rendering"
  | "done"
  | "failed";

export type Site = "US" | "UK" | "DE" | "JP";
export type DataSource = "csv" | "sorftime";
export type Sentiment = "积极" | "中性" | "消极";

// ── 任务 ─────────────────────────────────────────────────

export interface TaskConfig {
  max_reviews: number;
  batch_size: number;
  template: string;
}

export interface TaskCreate {
  asin: string;
  site: Site;
  source: DataSource;
  upload_id?: string;
  config?: TaskConfig;
}

export interface TaskResponse {
  id: string;
  asin: string;
  site: string;
  source: string;
  status: TaskStatus;
  progress: number;
  current_phase: number;
  phase_message: string | null;
  config: Record<string, unknown>;
  total_reviews: number;
  persona_count: number;
  avg_rating: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  tasks: TaskResponse[];
  total: number;
}

// ── 上传 ─────────────────────────────────────────────────

export interface UploadResponse {
  upload_id: string;
  original_name: string;
  size_bytes: number;
  review_count: number;
  preview_rows: Record<string, unknown>[];
}

export interface UploadHistoryResponse {
  uploads: UploadRecord[];
  total: number;
}

export interface UploadRecord {
  id: string;
  original_name: string;
  size_bytes: number;
  review_count: number;
  created_at: string;
}

// ── 评论 ─────────────────────────────────────────────────

export interface ReviewResponse {
  id: string;
  task_id: string;
  review_id: string | null;
  title: string | null;
  body: string;
  rating: number;
  author: string | null;
  date: string | null;
  helpful_count: number;
  verified_purchase: boolean;
  images: string[] | null;
  variant: string | null;
  country: string | null;
  created_at: string;
}

export interface ReviewListResponse {
  reviews: ReviewResponse[];
  total: number;
}

// ── 打标结果 ─────────────────────────────────────────────

export interface TaggedReviewResponse {
  id: string;
  task_id: string;
  review_id: string;
  sentiment: string | null;
  info_score: number;
  tags: Record<string, string>;
  review_body: string | null;
  review_rating: number | null;
  created_at: string;
}

export interface TaggedReviewListResponse {
  tagged_reviews: TaggedReviewResponse[];
  total: number;
}

// ── 用户画像 ─────────────────────────────────────────────

export interface GoldenSampleResponse {
  id: string;
  sentiment: string | null;
  sentiment_class: string | null;
  review_body: string | null;
  review_rating: number | null;
}

export interface PersonaResponse {
  id: string;
  task_id: string;
  name: string;
  count: number;
  dimension: string | null;
  tags: Record<string, string>;
  color: string;
  summary: string | null;
  golden_samples: GoldenSampleResponse[];
  created_at: string;
}

// ── 报告 ─────────────────────────────────────────────────

export interface ReportResponse {
  insights_md: string | null;
  stats: Record<string, unknown> | null;
  chart_configs: Record<string, unknown> | null;
  html_content: string | null;
  template_name: string;
  created_at: string;
}

// ── SSE ──────────────────────────────────────────────────

export interface SSEProgressEvent {
  phase: number;
  phase_name: string;
  message: string;
  progress: number;
}

export interface SSEDoneEvent {
  task_id: string;
  status: "done";
  total_reviews: number;
}

export interface SSEErrorEvent {
  phase: number;
  message: string;
}
