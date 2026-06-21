// 공통 상태 배지 컴포넌트.
// Products/Orders/Users 페이지가 모두 이 컴포넌트를 사용한다.
// props 를 바꾸면 모든 사용처가 영향받는다. (scenario/shared-component-change)

import "./StatusBadge.css";

export interface StatusBadgeProps {
  /** 표시할 상태 코드 (예: ACTIVE, PAID, VIP) */
  status: string;
  /** 선택적 표시 라벨 (없으면 status 를 그대로 표시) */
  label?: string;
}

// 상태 코드 -> 색상 톤(CSS 클래스 접미사) 매핑
const TONE: Record<string, string> = {
  // product
  DRAFT: "neutral",
  ACTIVE: "success",
  SOLD_OUT: "danger",
  ARCHIVED: "neutral",
  // order
  PENDING: "warning",
  PAID: "info",
  SHIPPED: "info",
  DELIVERED: "success",
  CANCELLED: "danger",
  // user grade
  BRONZE: "neutral",
  SILVER: "info",
  GOLD: "warning",
  VIP: "success",
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const tone = TONE[status] ?? "neutral";
  return (
    <span className={`status-badge status-badge--${tone}`} data-testid="status-badge">
      {label ?? status}
    </span>
  );
}
