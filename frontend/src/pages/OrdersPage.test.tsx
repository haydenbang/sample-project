import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";

// Mock dependencies
vi.mock("../hooks/useOrders");
vi.mock("../components/common/DataTable", () => ({
  DataTable: ({ columns, rows, rowKey }: any) => (
    <table>
      <thead>
        <tr>
          {columns.map((col: any) => (
            <th key={col.key}>{col.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row: any) => (
          <tr key={rowKey(row)}>
            {columns.map((col: any) => (
              <td key={col.key}>
                {col.render ? col.render(row) : row[col.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  ),
}));

vi.mock("../components/common/PageHeader", () => ({
  PageHeader: ({ title, description }: any) => (
    <div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  ),
}));

vi.mock("../components/common/StatusBadge", () => ({
  StatusBadge: ({ status }: any) => <span data-testid="status-badge">{status}</span>,
}));

vi.mock("../utils/format", () => ({
  formatKRW: (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return "₩0";
    return `₩${amount.toLocaleString()}`;
  },
  formatDiscount: (subtotal: number, discount: number) => {
    if (!subtotal) return "0%";
    return `${Math.round((discount / subtotal) * 100)}%`;
  },
}));

import { useOrders } from "../hooks/useOrders";
import { OrdersPage } from "./OrdersPage";

const mockUseOrders = vi.mocked(useOrders);

describe("OrdersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("final_amount field rendering", () => {
    it("renders final_amount column header", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("최종금액")).toBeInTheDocument();
    });

    it("renders final_amount value correctly for a valid order", () => {
      const mockOrders = [
        {
          id: "order-1",
          user_id: "user-1",
          status: "completed",
          subtotal: 10000,
          discount_amount: 1000,
          total: 9000,
          final_amount: 9000,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      // formatKRW(9000) => ₩9,000
      expect(screen.getByText("₩9,000")).toBeInTheDocument();
    });

    it("renders final_amount of 0 correctly", () => {
      const mockOrders = [
        {
          id: "order-2",
          user_id: "user-2",
          status: "pending",
          subtotal: 5000,
          discount_amount: 5000,
          total: 0,
          final_amount: 0,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      // formatKRW(0) => ₩0
      const zeroAmounts = screen.getAllByText("₩0");
      expect(zeroAmounts.length).toBeGreaterThan(0);
    });

    it("handles null final_amount gracefully", () => {
      const mockOrders = [
        {
          id: "order-3",
          user_id: "user-3",
          status: "pending",
          subtotal: 10000,
          discount_amount: 0,
          total: 10000,
          final_amount: null,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders as any,
        loading: false,
        error: null,
      });

      // Should not throw
      expect(() => render(<OrdersPage />)).not.toThrow();
      // formatKRW(null) => ₩0
      expect(screen.getAllByText("₩0").length).toBeGreaterThan(0);
    });

    it("handles undefined final_amount gracefully", () => {
      const mockOrders = [
        {
          id: "order-4",
          user_id: "user-4",
          status: "pending",
          subtotal: 10000,
          discount_amount: 0,
          total: 10000,
          // final_amount is undefined (not provided)
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders as any,
        loading: false,
        error: null,
      });

      // Should not throw
      expect(() => render(<OrdersPage />)).not.toThrow();
      expect(screen.getAllByText("₩0").length).toBeGreaterThan(0);
    });

    it("renders large final_amount correctly", () => {
      const mockOrders = [
        {
          id: "order-5",
          user_id: "user-5",
          status: "completed",
          subtotal: 1000000,
          discount_amount: 100000,
          total: 900000,
          final_amount: 900000,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩900,000")).toBeInTheDocument();
    });

    it("renders multiple orders with different final_amounts", () => {
      const mockOrders = [
        {
          id: "order-6",
          user_id: "user-6",
          status: "completed",
          subtotal: 10000,
          discount_amount: 1000,
          total: 9000,
          final_amount: 9000,
        },
        {
          id: "order-7",
          user_id: "user-7",
          status: "completed",
          subtotal: 20000,
          discount_amount: 2000,
          total: 18000,
          final_amount: 18000,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩9,000")).toBeInTheDocument();
      expect(screen.getByText("₩18,000")).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("shows loading message when loading", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: true,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("불러오는 중…")).toBeInTheDocument();
    });

    it("does not render table while loading", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: true,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.queryByRole("table")).not.toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message when error occurs", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: "주문을 불러오는 데 실패했습니다.",
      });

      render(<OrdersPage />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("주문을 불러오는 데 실패했습니다.")).toBeInTheDocument();
    });

    it("does not render table when error occurs", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: "Error",
      });

      render(<OrdersPage />);

      expect(screen.queryByRole("table")).not.toBeInTheDocument();
    });
  });

  describe("page structure", () => {
    it("renders page header with correct title", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("주문 관리")).toBeInTheDocument();
    });

    it("renders page header with correct description", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("주문 내역과 결제 금액을 조회합니다.")).toBeInTheDocument();
    });

    it("renders all column headers", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("주문번호")).toBeInTheDocument();
      expect(screen.getByText("회원ID")).toBeInTheDocument();
      expect(screen.getByText("상태")).toBeInTheDocument();
      expect(screen.getByText("합계")).toBeInTheDocument();
      expect(screen.getByText("할인")).toBeInTheDocument();
      expect(screen.getByText("결제금액")).toBeInTheDocument();
      expect(screen.getByText("최종금액")).toBeInTheDocument();
    });

    it("renders table when not loading and no error", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByRole("table")).toBeInTheDocument();
    });
  });

  describe("order data rendering", () => {
    it("renders order id", () => {
      const mockOrders = [
        {
          id: "order-100",
          user_id: "user-abc",
          status: "completed",
          subtotal: 10000,
          discount_amount: 0,
          total: 10000,
          final_amount: 10000,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("order-100")).toBeInTheDocument();
    });

    it("renders status badge", () => {
      const mockOrders = [
        {
          id: "order-101",
          user_id: "user-xyz",
          status: "pending",
          subtotal: 5000,
          discount_amount: 500,
          total: 4500,
          final_amount: 4500,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByTestId("status-badge")).toBeInTheDocument();
      expect(screen.getByTestId("status-badge")).toHaveTextContent("pending");
    });

    it("renders subtotal with formatKRW", () => {
      const mockOrders = [
        {
          id: "order-102",
          user_id: "user-1",
          status: "completed",
          subtotal: 15000,
          discount_amount: 1500,
          total: 13500,
          final_amount: 13500,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩15,000")).toBeInTheDocument();
    });

    it("renders discount amount with percentage", () => {
      const mockOrders = [
        {
          id: "order-103",
          user_id: "user-1",
          status: "completed",
          subtotal: 10000,
          discount_amount: 2000,
          total: 8000,
          final_amount: 8000,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      // discount rendered as "₩2,000 (20%)"
      expect(screen.getByText(/₩2,000.*20%/)).toBeInTheDocument();
    });

    it("renders empty table when orders array is empty", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByRole("table")).toBeInTheDocument();
      const rows = screen.queryAllByRole("row");
      // Only header row
      expect(rows).toHaveLength(1);
    });
  });

  describe("final_amount edge cases", () => {
    it("renders final_amount as integer (non-nullable per spec)", () => {
      const mockOrders = [
        {
          id: "order-200",
          user_id: "user-200",
          status: "completed",
          subtotal: 99999,
          discount_amount: 9999,
          total: 90000,
          final_amount: 90000,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩90,000")).toBeInTheDocument();
    });

    it("renders final_amount of 1 correctly", () => {
      const mockOrders = [
        {
          id: "order-201",
          user_id: "user-201",
          status: "completed",
          subtotal: 1,
          discount_amount: 0,
          total: 1,
          final_amount: 1,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getAllByText("₩1").length).toBeGreaterThan(0);
    });

    it("handles negative final_amount edge case", () => {
      const mockOrders = [
        {
          id: "order-202",
          user_id: "user-202",
          status: "refunded",
          subtotal: 10000,
          discount_amount: 0,
          total: -10000,
          final_amount: -10000,
        },
      ];

      mockUseOrders.mockReturnValue({
        orders: mockOrders as any,
        loading: false,
        error: null,
      });

      expect(() => render(<OrdersPage />)).not.toThrow();
    });
  });
});