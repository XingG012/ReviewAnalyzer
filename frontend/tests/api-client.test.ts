/** API Client 单元测试 */

import { describe, it, expect } from "vitest";
import { getExportUrl } from "../src/lib/api-client";
import { taskCreateSchema, toTaskCreatePayload } from "../src/lib/validators";

describe("API Client", () => {
  it("getExportUrl generates correct URL for csv", () => {
    const url = getExportUrl("abc-123", "csv");
    expect(url).toContain("/tasks/abc-123/export/csv");
  });

  it("getExportUrl generates correct URL for md", () => {
    const url = getExportUrl("abc-123", "md");
    expect(url).toContain("/tasks/abc-123/export/md");
  });
});

describe("Zod Validators", () => {
  it("accepts valid ASIN", () => {
    const result = taskCreateSchema.safeParse({
      asin: "B0DGV4T6BK",
      site: "US",
      source: "csv",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid ASIN (too short)", () => {
    const result = taskCreateSchema.safeParse({
      asin: "ABC",
      site: "US",
      source: "csv",
    });
    expect(result.success).toBe(false);
  });

  it("rejects invalid ASIN (lowercase)", () => {
    const result = taskCreateSchema.safeParse({
      asin: "b0dgv4t6bk",
      site: "US",
      source: "csv",
    });
    expect(result.success).toBe(false);
  });

  it("toTaskCreatePayload uppercases ASIN", () => {
    const payload = toTaskCreatePayload({
      asin: "b0dgv4t6bk",
      site: "US",
      source: "csv",
      config: { max_reviews: 500, batch_size: 20, template: "premium-gold" },
    });
    expect(payload.asin).toBe("B0DGV4T6BK");
  });
});
