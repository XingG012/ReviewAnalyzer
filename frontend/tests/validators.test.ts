/** Zod 校验 Schema 单元测试 — taskCreateSchema 与 toTaskCreatePayload */

import { describe, expect, it } from "vitest";
import { taskCreateSchema, toTaskCreatePayload, type TaskCreateForm } from "../src/lib/validators";

const validInput: TaskCreateForm = {
  asin: "B0DGV4T6BK",
  site: "US",
  source: "csv",
  upload_id: "550e8400-e29b-41d4-a716-446655440000",
  config: { max_reviews: 500, batch_size: 20, template: "premium-gold" },
};

describe("taskCreateSchema", () => {
  it("接受合法输入", () => {
    const result = taskCreateSchema.safeParse(validInput);
    expect(result.success).toBe(true);
  });

  it("ASIN 长度不足时返回「ASIN 必须为 10 位」", () => {
    const result = taskCreateSchema.safeParse({ ...validInput, asin: "ABC" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.message)).toContain("ASIN 必须为 10 位");
    }
  });

  it("ASIN 含小写字母时返回格式错误", () => {
    const result = taskCreateSchema.safeParse({ ...validInput, asin: "b0dgv4t6bk" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.message)).toContain(
        "ASIN 格式不正确，应为 10 位字母数字组合",
      );
    }
  });

  it("ASIN 含非法字符时返回格式错误", () => {
    const result = taskCreateSchema.safeParse({ ...validInput, asin: "B0DG-V4T6B" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.message)).toContain(
        "ASIN 格式不正确，应为 10 位字母数字组合",
      );
    }
  });

  it("max_reviews 低于 10 时报错", () => {
    const result = taskCreateSchema.safeParse({
      ...validInput,
      config: { ...validInput.config, max_reviews: 9 },
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.message)).toContain("评论数量应在 10-2000 之间");
    }
  });

  it("max_reviews 高于 2000 时报错", () => {
    const result = taskCreateSchema.safeParse({
      ...validInput,
      config: { ...validInput.config, max_reviews: 2001 },
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.message)).toContain("评论数量应在 10-2000 之间");
    }
  });

  it("upload_id 非 UUID 时被拒绝", () => {
    const result = taskCreateSchema.safeParse({ ...validInput, upload_id: "not-a-uuid" });
    expect(result.success).toBe(false);
  });

  it("site 非法值被拒绝", () => {
    const result = taskCreateSchema.safeParse({ ...validInput, site: "CN" });
    expect(result.success).toBe(false);
  });

  it("缺省 site/source/config 时填充默认值", () => {
    const result = taskCreateSchema.safeParse({ asin: "B0DGV4T6BK" });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.site).toBe("US");
      expect(result.data.source).toBe("csv");
      expect(result.data.config).toEqual({
        max_reviews: 500,
        batch_size: 20,
        template: "premium-gold",
      });
    }
  });
});

describe("toTaskCreatePayload", () => {
  it("将 ASIN 转为大写", () => {
    const payload = toTaskCreatePayload({ ...validInput, asin: "b0dgv4t6bk" });
    expect(payload.asin).toBe("B0DGV4T6BK");
  });

  it("透传 site/source/config/upload_id", () => {
    const payload = toTaskCreatePayload(validInput);
    expect(payload.site).toBe("US");
    expect(payload.source).toBe("csv");
    expect(payload.upload_id).toBe(validInput.upload_id);
    expect(payload.config).toEqual(validInput.config);
  });
});
