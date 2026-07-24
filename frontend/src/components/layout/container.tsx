/** 页面内容容器 */

export function Container({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>;
}
