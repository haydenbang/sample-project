// 상품 목록 페이지.
// 공통 컴포넌트(PageHeader, DataTable, StatusBadge) 와 useProducts 훅을 사용한다.

import { DataTable, type Column } from "../components/common/DataTable";
import { PageHeader } from "../components/common/PageHeader";
import { StatusBadge } from "../components/common/StatusBadge";
import { useProducts } from "../hooks/useProducts";
import type { Product } from "../types/product";
import { formatKRW } from "../utils/format";

const columns: Column<Product>[] = [
  { key: "id", header: "ID" },
  { key: "name", header: "상품명" },
  { key: "category", header: "카테고리" },
  { key: "price", header: "단가", render: (p) => formatKRW(p.price) },
  { key: "stock", header: "재고" },
  { key: "status", header: "상태", render: (p) => <StatusBadge status={p.status} /> },
];

export function ProductsPage() {
  const { products, loading, error } = useProducts();

  return (
    <section>
      <PageHeader title="상품 관리" description="등록된 상품을 조회합니다." />
      {loading && <p>불러오는 중…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && (
        <DataTable columns={columns} rows={products} rowKey={(p) => p.id} />
      )}
    </section>
  );
}
