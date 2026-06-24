import { describe, expect, it } from "vitest";
import { clamp, formatSpeed } from "../../web/src/utils/format";

describe("web utils", () => {
  it("formats speed", () => {
    expect(formatSpeed(10)).toBe("36 km/h");
  });

  it("clamps values", () => {
    expect(clamp(12, 0, 10)).toBe(10);
    expect(clamp(-1, 0, 10)).toBe(0);
    expect(clamp(5, 0, 10)).toBe(5);
  });
});