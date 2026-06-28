Looking at the change event, `final_amount` has been added to `OrderOut`. I need to:

1. Add `final_amount` to the `Order` type usage (the type definition itself is in `../types/order`, but this file needs to render it)
2. Add a column for `final_amount` in the table

```tsx
// 주문 목록 페이지.
// 공통 컴포넌트와 useOrders 훅을 사용한다.
// 주문 응답 필드(total 등)에 의존한다. (scenario/api-spec-change)

import { DataTable, type Column } from "../components/common/DataTable";
import { PageHeader } from "../components/common/PageHeader";
import { StatusBadge } from "../components/common/StatusBadge";
import { useOrders } from "../hooks/useOrders";
import type { Order } from "../types/order";
import { formatDiscount, formatKRW } from "../utils/format";

const columns: Column<Order>[] = [
  { key: "id", header: "주문번호" },
  { key: "user_id", header: "회원ID" },
  { key: "status", header: "상태", render: (o) => <StatusBadge status={o.status} /> },
  { key: "subtotal", header: "합계", render: (o) => formatKRW(o.subtotal) },
  {
    key: "discount_amount",
    header: "할인",
    render: (o) => `${formatKRW(o.discount_amount)} (${formatDiscount(o.subtotal, o.discount_amount)})`,
  },
  { key: "total", header: "결제금액", render: (o) => formatKRW(o.total) },
  { key: "final_amount", header: "최종금액", render: (o) => formatKRW(o.final_amount) },
];

export function OrdersPage() {
  const { orders, loading, error } = useOrders();

  return (
    <section>
      <PageHeader title="주문 관리" description="주문 내역과 결제 금액을 조회합니다." />
      {loading && <p>불러오는 중…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && (
        <DataTable columns={columns} rows={orders} rowKey={(o) => o.id} />
      )}
    </section>
  );
}
```