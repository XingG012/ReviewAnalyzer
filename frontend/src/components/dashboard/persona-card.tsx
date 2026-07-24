/** 用户画像卡片 */

import type { PersonaResponse } from "@/types";

export function PersonaCard({ persona }: { persona: PersonaResponse }) {
  return (
    <div className="rounded-lg border bg-card p-5 hover:shadow-sm transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-lg">{persona.name}</h3>
        <span
          className="text-sm px-2 py-0.5 rounded"
          style={{
            background: `${persona.color}20`,
            color: persona.color,
            fontFamily: "var(--font-mono)",
          }}
        >
          {persona.count} 人
        </span>
      </div>

      {/* Summary */}
      {persona.summary && <p className="text-sm text-muted-foreground mb-3">{persona.summary}</p>}

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {Object.entries(persona.tags).map(([k, v]) => (
          <span key={k} className="text-xs px-2 py-0.5 rounded-full border bg-muted/50">
            <span className="text-muted-foreground">{k}:</span>{" "}
            <span className="font-medium">{v}</span>
          </span>
        ))}
      </div>

      {/* Golden Samples */}
      {persona.golden_samples.length > 0 && (
        <div className="space-y-2 mt-3 pt-3 border-t">
          <p className="text-xs text-muted-foreground font-medium">代表性评论</p>
          {persona.golden_samples.slice(0, 2).map((gs, i) => (
            <blockquote
              key={i}
              className={`text-xs italic pl-3 border-l-2 ${
                gs.sentiment === "positive" ? "border-emerald-500" : "border-red-500"
              }`}
            >
              {gs.review_body?.slice(0, 120)}
              {gs.review_body && gs.review_body.length > 120 && "…"}
            </blockquote>
          ))}
        </div>
      )}
    </div>
  );
}
