/** 首页渲染测试 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import HomePage from "../src/app/page";

describe("HomePage", () => {
  it("renders the hero title", () => {
    render(<HomePage />);
    expect(screen.getByText("Amazon 评论深度分析平台")).toBeDefined();
  });

  it("renders the CTA button linking to /tasks", () => {
    render(<HomePage />);
    const link = screen.getByRole("link", { name: /开始分析/ });
    expect(link).toBeDefined();
    expect(link.getAttribute("href")).toBe("/tasks");
  });

  it("renders three feature cards", () => {
    render(<HomePage />);
    expect(screen.getByText("22 维 AI 打标")).toBeDefined();
    expect(screen.getByText("14 章洞察报告")).toBeDefined();
    expect(screen.getByText("6 套可视化看板")).toBeDefined();
  });
});
