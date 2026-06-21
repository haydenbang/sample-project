import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "../components/common/StatusBadge";

describe("StatusBadge", () => {
  it("status 코드를 그대로 표시한다", () => {
    render(<StatusBadge status="ACTIVE" />);
    expect(screen.getByTestId("status-badge")).toHaveTextContent("ACTIVE");
  });

  it("label 이 있으면 label 을 표시한다", () => {
    render(<StatusBadge status="ACTIVE" label="판매중" />);
    expect(screen.getByTestId("status-badge")).toHaveTextContent("판매중");
  });

  it("상태별 톤 클래스를 적용한다", () => {
    render(<StatusBadge status="CANCELLED" />);
    expect(screen.getByTestId("status-badge")).toHaveClass("status-badge--danger");
  });

  it("알 수 없는 상태는 neutral 톤을 사용한다", () => {
    render(<StatusBadge status="UNKNOWN" />);
    expect(screen.getByTestId("status-badge")).toHaveClass("status-badge--neutral");
  });
});
