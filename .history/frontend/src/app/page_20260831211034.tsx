// Amazon 评论深度分析平台 - 首页

// lucide-react是一个图标库。（右箭头、柱状图、文件、调色板）
import { ArrowRight, BarChart3, FileText, Palette } from "lucide-react";
// next/link是Next.js提供的页面跳转组件，替代原生 HTML 的 `<a>` 标签。
import Link from "next/link";
// Container是一个布局组件，用于包裹页面内容并提供统一的样式。
import { Container } from "@/components/layout/container";

const features = [
  {
    icon: BarChart3,
    title: "22 维 AI 打标",
    desc: "人群性别、年龄段、使用场景、产品质量…全方位透视评论数据",
  },
  {
    icon: FileText,
    title: "14 章洞察报告",
    desc: "市场定位、用户画像、产品优劣势…AI 驱动深度分析",
  },
  {
    icon: Palette,
    title: "6 套可视化看板",
    desc: "黑金奢华 / 赛博朋克 / 极简白蓝…适配不同汇报场景",
  },
];

export default function HomePage() {
  return (
    <Container>
      <section className="py-16 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Amazon 评论深度分析平台</h1>
        <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
          输入 ASIN 或上传 CSV，AI 自动完成 22 维度打标与 14 章洞察报告， 输出 6
          套可切换主题的专业可视化看板。
        </p>
        <Link
          href="/tasks"
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
        >
          开始分析 <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
      <section className="mt-8 grid gap-6 sm:grid-cols-3">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-xl border bg-card p-6 hover:shadow-md transition-shadow"
          >
            <f.icon className="h-8 w-8 text-primary mb-3" />
            <h3 className="font-semibold text-lg">{f.title}</h3>
            <p className="mt-1 text-muted-foreground text-sm">{f.desc}</p>
          </div>
        ))}
      </section>
    </Container>
  );
}
