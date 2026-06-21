import { describe, expect, it } from "vitest";

import { formatDiscount, formatKRW } from "../utils/format";

describe("formatKRW", () => {
  it("천 단위 구분 기호와 원을 붙인다", () => {
    expect(formatKRW(74100)).toBe("74,100원");
  });
});

describe("formatDiscount", () => {
  it("할인율을 백분율로 계산한다", () => {
    expect(formatDiscount(78000, 3900)).toBe("5%");
  });

  it("subtotal 이 0이면 0% 를 반환한다", () => {
    expect(formatDiscount(0, 0)).toBe("0%");
  });
});
