/** 主题类型定义 */

export type ThemeId =
  | "premium-gold"
  | "dark-tech"
  | "linear-minimal"
  | "posthog-analytics"
  | "stripe-executive"
  | "warm-editorial";

export interface ThemeTokens {
  /* Typography */
  "--font-display": string;
  "--font-body": string;
  "--font-mono": string;
  /* Surfaces */
  "--bg": string;
  "--surface": string;
  "--surface-elevated": string;
  "--surface-recessed": string;
  /* Borders */
  "--border": string;
  "--border-bright": string;
  "--border-accent": string;
  /* Text */
  "--text": string;
  "--text-dim": string;
  "--text-muted": string;
  /* Accent */
  "--accent": string;
  "--accent-bright": string;
  "--accent-dim": string;
  /* Semantic */
  "--green": string;
  "--red": string;
  "--blue": string;
  "--orange": string;
  /* Charts */
  "--chart-1": string;
  "--chart-2": string;
  "--chart-3": string;
  "--chart-4": string;
  "--chart-5": string;
}

export interface ThemeDefinition {
  id: ThemeId;
  name: string;
  description: string;
  tokens: ThemeTokens;
}
