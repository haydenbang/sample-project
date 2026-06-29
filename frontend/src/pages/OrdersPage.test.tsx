import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OrdersPage } from "./OrdersPage";
import { useOrders } from "../hooks/useOrders";
import type { Order } from "../types/order";

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
    return `${((discount / subtotal) * 100).toFixed(1)}%`;
  },
}));

const mockUseOrders = vi.mocked(useOrders);

const createOrder = (overrides: Partial<Order> = {}): Order => ({
  id: "order-1",
  user_id: "user-1",
  status: "completed",
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

  describe("rendering states", () => {
    it("renders page header with correct title and description", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("주문 관리")).toBeInTheDocument();
      expect(screen.getByText("주문 내역과 결제 금액을 조회합니다.")).toBeInTheDocument();
    });

    it("shows loading message when loading is true", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: true,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("불러오는 중…")).toBeInTheDocument();
    });

    it("does not show table when loading", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: true,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.queryByRole("table")).not.toBeInTheDocument();
    });

    it("shows error message when error exists", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: "서버 오류가 발생했습니다.",
      });

      render(<OrdersPage />);

      const alert = screen.getByRole("alert");
      expect(alert).toBeInTheDocument();
      expect(alert).toHaveTextContent("서버 오류가 발생했습니다.");
    });

    it("does not show table when error exists", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: "에러 발생",
      });

      render(<OrdersPage />);

      expect(screen.queryByRole("table")).not.toBeInTheDocument();
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

  describe("column headers", () => {
    beforeEach(() => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });
    });

    it("renders all column headers including final_amount", () => {
      render(<OrdersPage />);

      expect(screen.getByText("주문번호")).toBeInTheDocument();
      expect(screen.getByText("회원ID")).toBeInTheDocument();
      expect(screen.getByText("상태")).toBeInTheDocument();
      expect(screen.getByText("합계")).toBeInTheDocument();
      expect(screen.getByText("할인")).toBeInTheDocument();
      expect(screen.getByText("결제금액")).toBeInTheDocument();
      expect(screen.getByText("최종금액")).toBeInTheDocument();
    });
  });

  describe("final_amount field handling", () => {
    it("renders final_amount correctly with valid integer value", () => {
      const order = createOrder({ final_amount: 9000 });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩9,000")).toBeInTheDocument();
    });

    it("renders final_amount of zero correctly", () => {
      const order = createOrder({ final_amount: 0 });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      // Should show ₩0 for final_amount (and possibly other zero fields)
      const zeroAmounts = screen.getAllByText("₩0");
      expect(zeroAmounts.length).toBeGreaterThan(0);
    });

    it("handles final_amount when it is null (edge case)", () => {
      const order = createOrder({ final_amount: null as any });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      // Should not throw
      expect(() => render(<OrdersPage />)).not.toThrow();
      expect(screen.getAllByText("₩0").length).toBeGreaterThan(0);
    });

    it("handles final_amount when it is undefined (edge case)", () => {
      const order = createOrder({ final_amount: undefined as any });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      // Should not throw
      expect(() => render(<OrdersPage />)).not.toThrow();
      expect(screen.getAllByText("₩0").length).toBeGreaterThan(0);
    });

    it("renders large final_amount value correctly", () => {
      const order = createOrder({ final_amount: 1000000 });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩1,000,000")).toBeInTheDocument();
    });

    it("renders final_amount for multiple orders", () => {
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

      expect(screen.getByText("₩5,000")).toBeInTheDocument();
      expect(screen.getByText("₩15,000")).toBeInTheDocument();
      expect(screen.getByText("₩25,000")).toBeInTheDocument();
    });

    it("renders final_amount distinct from total when values differ", () => {
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

      expect(screen.getByText("₩9,000")).toBeInTheDocument();
      expect(screen.getByText("₩8,500")).toBeInTheDocument();
    });
  });

  describe("order data rendering", () => {
    it("renders order id correctly", () => {
      const order = createOrder({ id: "ORD-12345" });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("ORD-12345")).toBeInTheDocument();
    });

    it("renders user_id correctly", () => {
      const order = createOrder({ user_id: "USR-99" });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("USR-99")).toBeInTheDocument();
    });

    it("renders status badge", () => {
      const order = createOrder({ status: "pending" });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByTestId("status-badge")).toBeInTheDocument();
      expect(screen.getByTestId("status-badge")).toHaveTextContent("pending");
    });

    it("renders subtotal with formatKRW", () => {
      const order = createOrder({ subtotal: 20000 });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText("₩20,000")).toBeInTheDocument();
    });

    it("renders discount_amount with percentage", () => {
      const order = createOrder({ subtotal: 10000, discount_amount: 1000 });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.getByText(/₩1,000.*10\.0%/)).toBeInTheDocument();
    });

    it("renders empty orders list without errors", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      expect(() => render(<OrdersPage />)).not.toThrow();
      expect(screen.getByRole("table")).toBeInTheDocument();
    });
  });

  describe("edge cases", () => {
    it("does not show loading text when not loading", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.queryByText("불러오는 중…")).not.toBeInTheDocument();
    });

    it("does not show error when error is null", () => {
      mockUseOrders.mockReturnValue({
        orders: [],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("handles order with all fields set to 0", () => {
      const order = createOrder({
        subtotal: 0,
        discount_amount: 0,
        total: 0,
        final_amount: 0,
      });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      expect(() => render(<OrdersPage />)).not.toThrow();
    });

    it("renders correctly when final_amount equals total", () => {
      const order = createOrder({ total: 7500, final_amount: 7500 });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      render(<OrdersPage />);

      const amounts = screen.getAllByText("₩7,500");
      expect(amounts.length).toBeGreaterThanOrEqual(2);
    });

    it("handles negative final_amount gracefully", () => {
      const order = createOrder({ final_amount: -500 });
      mockUseOrders.mockReturnValue({
        orders: [order],
        loading: false,
        error: null,
      });

      expect(() => render(<OrdersPage />)).not.toThrow();
    });
  });
});