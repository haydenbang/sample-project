// 공통 상태 배지 컴포넌트.
// Products/Orders/Users 페이지가 모두 이 컴포넌트를 사용한다.
//
// [변경] props 를 변경했다. (scenario/shared-component-change)
//   - status -> value 로 이름 변경
//   - kind (product | order | grade) 필수 prop 추가: 도메인별로 색상 톤을 분리
// 이 변경으로 StatusBadge 를 사용하는 모든 페이지/테스트가 영향을 받는다.
//   영향 대상: pages/ProductsPage, pages/OrdersPage, pages/UsersPage,
//             __tests__/StatusBadge.test.tsx

import "./StatusBadge.css";

export type BadgeKind = "product" | "order" | "grade";

export interface StatusBadgeProps {
  /** 표시할 상태 코드 (예: ACTIVE, PAID, VIP) — 구버전 prop명: status */
  value: string;
  /** 상태 코드가 속한 도메인 (신규 필수 prop) */
  kind: BadgeKind;
  /** 선택적 표시 라벨 (없으면 value 를 그대로 표시) */
  label?: string;
}

// 도메인(kind) 별 상태 코드 -> 색상 톤 매핑
const TONE_BY_KIND: Record<BadgeKind, Record<string, string>> = {
  product: {
    DRAFT: "neutral",
    ACTIVE: "success",
    SOLD_OUT: "danger",
    ARCHIVED: "neutral",
  },
  order: {
    PENDING: "warning",
    PAID: "info",
    SHIPPED: "info",
    DELIVERED: "success",
    CANCELLED: "danger",
  },
  grade: {
    BRONZE: "neutral",
    SILVER: "info",
    GOLD: "warning",
    VIP: "success",
  },
};

export function StatusBadge({ value, kind, label }: StatusBadgeProps) {
  const tone = TONE_BY_KIND[kind][value] ?? "neutral";
  return (
    <span className={`status-badge status-badge--${tone}`} data-testid="status-badge">
      {label ?? value}
    </span>
  );
}
