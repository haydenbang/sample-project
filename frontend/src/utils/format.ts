// 표시용 포매팅 유틸.

export function formatKRW(amount: number): string {
  return `${amount.toLocaleString("ko-KR")}원`;
}

// 할인율 표시 (백엔드 할인 정책과 의미적으로 연동). scenario/discount-policy-change
export function formatDiscount(subtotal: number, discount: number): string {
  if (subtotal <= 0) return "0%";
  const rate = Math.round((discount / subtotal) * 100);
  return `${rate}%`;
}
