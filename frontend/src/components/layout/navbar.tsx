/** 顶部导航栏 */

"use client";

import { BarChart3 } from "lucide-react";
import Link from "next/link";

export function Navbar() {
  return (
    <nav className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold text-lg">
          <BarChart3 className="h-5 w-5 text-primary" />
          <span>ReviewAnalyzer</span>
        </Link>
        <div className="flex gap-4 text-muted-foreground text-sm">
          <Link href="/" className="hover:text-foreground transition-colors">
            首页
          </Link>
          <Link href="/tasks" className="hover:text-foreground transition-colors">
            任务
          </Link>
        </div>
        <div className="flex-1" />
      </div>
    </nav>
  );
}
