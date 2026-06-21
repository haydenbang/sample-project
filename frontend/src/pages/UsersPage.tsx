// 회원 목록 페이지.
// 공통 컴포넌트와 useUsers 훅을 사용한다.
// 회원 필드(grade 등)에 의존한다. (scenario/db-schema-change)

import { DataTable, type Column } from "../components/common/DataTable";
import { PageHeader } from "../components/common/PageHeader";
import { StatusBadge } from "../components/common/StatusBadge";
import { useUsers } from "../hooks/useUsers";
import type { User } from "../types/user";

const columns: Column<User>[] = [
  { key: "id", header: "ID" },
  { key: "email", header: "이메일" },
  { key: "full_name", header: "이름" },
  { key: "role", header: "권한" },
  { key: "grade", header: "등급", render: (u) => <StatusBadge status={u.grade} /> },
  { key: "is_active", header: "활성", render: (u) => (u.is_active ? "Y" : "N") },
];

export function UsersPage() {
  const { users, loading, error } = useUsers();

  return (
    <section>
      <PageHeader title="회원 관리" description="회원 등급과 상태를 조회합니다." />
      {loading && <p>불러오는 중…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && <DataTable columns={columns} rows={users} rowKey={(u) => u.id} />}
    </section>
  );
}
