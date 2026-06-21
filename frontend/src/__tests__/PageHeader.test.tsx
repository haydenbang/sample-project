import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageHeader } from "../components/common/PageHeader";

describe("PageHeader", () => {
  it("제목과 설명을 렌더링한다", () => {
    render(<PageHeader title="상품 관리" description="설명" />);
    expect(screen.getByRole("heading", { name: "상품 관리" })).toBeInTheDocument();
    expect(screen.getByText("설명")).toBeInTheDocument();
  });

  it("actions 영역을 렌더링한다", () => {
    render(<PageHeader title="t" actions={<button>추가</button>} />);
    expect(screen.getByRole("button", { name: "추가" })).toBeInTheDocument();
  });
});
