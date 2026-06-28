import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OrdersPage } from "./OrdersPage";

// Mock hooks and components
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
    return `${((discount / subtotal) * 100).toFixed(0)}%`;
  },
}));

import { useOrders } from "../hooks/useOrders";

const mockUseOrders = vi.mocked(useOrders);

const createOrder = (overrides = {}) => ({
  id: "order-1",
  user_id: "user-1",
  status: "PENDING",
  subtotal: 10000,
  discount_amount: 1000,
  total: 9000,
  final_amount: 9000,
  ...overrides,
});

describe("OrdersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading state", () => {
    it("should render loading message when loading is true", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: true,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("불러오는 중…")).toBeDefined();
    });

    it("should not render table when loading", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: true,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.queryByRole("table")).toBeNull();
    });
  });

  describe("Error state", () => {
    it("should render error message when error exists", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: "Failed to fetch orders",
      });

      render(<OrdersPage />);

      expect(screen.getByRole("alert")).toBeDefined();
      expect(screen.getByText("Failed to fetch orders")).toBeDefined();
    });

    it("should not render table when error exists", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: "Some error",
      });

      render(<OrdersPage />);

      expect(screen.queryByRole("table")).toBeNull();
    });
  });

  describe("Page header", () => {
    it("should render page header with correct title", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("주문 관리")).toBeDefined();
    });

    it("should render page header with correct description", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("주문 내역과 결제 금액을 조회합니다.")).toBeDefined();
    });
  });

  describe("Table columns", () => {
    it("should render all column headers including final_amount", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("주문번호")).toBeDefined();
      expect(screen.getByText("회원ID")).toBeDefined();
      expect(screen.getByText("상태")).toBeDefined();
      expect(screen.getByText("합계")).toBeDefined();
      expect(screen.getByText("할인")).toBeDefined();
      expect(screen.getByText("결제금액")).toBeDefined();
      expect(screen.getByText("최종금액")).toBeDefined();
    });
  });

  describe("final_amount field rendering", () => {
    it("should render final_amount correctly for a normal order", () => {
      const order = createOrder({ final_amount: 9000 });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩9,000")).toBeDefined();
    });

    it("should render final_amount as zero when value is 0", () => {
      const order = createOrder({ final_amount: 0 });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      const zeroCells = screen.getAllByText("₩0");
      expect(zeroCells.length).toBeGreaterThan(0);
    });

    it("should handle final_amount with large values", () => {
      const order = createOrder({ final_amount: 1000000 });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩1,000,000")).toBeDefined();
    });

    it("should handle final_amount when it differs from total", () => {
      const order = createOrder({
        total: 9000,
        final_amount: 8500,
      });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩8,500")).toBeDefined();
      expect(screen.getByText("₩9,000")).toBeDefined();
    });

    it("should handle null final_amount gracefully", () => {
      const order = createOrder({ final_amount: null });

      mockUseOrders.mockReturnValue({
        orders: [order as any],
        loading: false,
        error: null,
      });

      // Should not throw
      expect(() => render(<OrdersPage />)).not.toThrow();

      const zeroCells = screen.getAllByText("₩0");
      expect(zeroCells.length).toBeGreaterThan(0);
    });

    it("should handle undefined final_amount gracefully", () => {
      const { final_amount, ...orderWithoutFinalAmount } = createOrder();
      const order = orderWithoutFinalAmount;

      mockUseOrders.mockReturnValue({
        orders: [order as any],
        loading: false,
        error: null,
      });

      // Should not throw
      expect(() => render(<OrdersPage />)).not.toThrow();

      const zeroCells = screen.getAllByText("₩0");
      expect(zeroCells.length).toBeGreaterThan(0);
    });

    it("should render final_amount column separately from total column", () => {
      const order = createOrder({
        total: 9000,
        final_amount: 7500,
      });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩9,000")).toBeDefined();
      expect(screen.getByText("₩7,500")).toBeDefined();
    });
  });

  describe("Multiple orders rendering", () => {
    it("should render multiple orders with their final_amount values", () => {
      const orders = [
        createOrder({ id: "order-1", final_amount: 5000 }),
        createOrder({ id: "order-2", final_amount: 15000 }),
        createOrder({ id: "order-3", final_amount: 25000 }),
      ];

      mockUseOrders.mockReturnValue({
        orders,
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩5,000")).toBeDefined();
      expect(screen.getByText("₩15,000")).toBeDefined();
      expect(screen.getByText("₩25,000")).toBeDefined();
    });

    it("should render empty table when orders is empty array", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByRole("table")).toBeDefined();
      expect(screen.getByText("최종금액")).toBeDefined();
    });
  });

  describe("Order status rendering", () => {
    it("should render status badge for each order", () => {
      const order = createOrder({ status: "COMPLETED" });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toBeDefined();
      expect(statusBadge.textContent).toBe("COMPLETED");
    });

    it("should render PENDING status", () => {
      const order = createOrder({ status: "PENDING" });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByTestId("status-badge").textContent).toBe("PENDING");
    });

    it("should render CANCELLED status", () => {
      const order = createOrder({ status: "CANCELLED" });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByTestId("status-badge").textContent).toBe("CANCELLED");
    });
  });

  describe("Discount rendering", () => {
    it("should render discount amount and percentage", () => {
      const order = createOrder({
        subtotal: 10000,
        discount_amount: 1000,
      });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩1,000 (10%)")).toBeDefined();
    });

    it("should handle zero discount amount", () => {
      const order = createOrder({
        subtotal: 10000,
        discount_amount: 0,
      });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩0 (0%)")).toBeDefined();
    });
  });

  describe("Integration: complete order rendering", () => {
    it("should render all fields of an order correctly including final_amount", () => {
      const order = createOrder({
        id: "order-123",
        user_id: "user-456",
        status: "COMPLETED",
        subtotal: 20000,
        discount_amount: 2000,
        total: 18000,
        final_amount: 18000,
      });

      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("order-123")).toBeDefined();
      expect(screen.getByText("user-456")).toBeDefined();
      expect(screen.getByTestId("status-badge").textContent).toBe("COMPLETED");
      expect(screen.getByText("₩20,000")).toBeDefined();
      expect(screen.getByText("₩2,000 (10%)")).toBeDefined();
      // Both total and final_amount are 18000
      const cells18000 = screen.getAllByText("₩18,000");
      expect(cells18000.length).toBe(2);
    });
  });
});