/** API Client 单元测试 */

import { describe, it, expect } from "vitest";
import { getExportUrl } from "../src/lib/api-client";

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
