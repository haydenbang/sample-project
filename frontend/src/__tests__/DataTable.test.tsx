import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataTable, type Column } from "../components/common/DataTable";

interface Row {
  id: number;
  name: string;
}

const columns: Column<Row>[] = [
  { key: "id", header: "ID" },
  { key: "name", header: "이름", render: (r) => <strong>{r.name}</strong> },
];

describe("DataTable", () => {
  it("행 데이터를 렌더링한다", () => {
    render(
      <DataTable
        columns={columns}
        rows={[{ id: 1, name: "키보드" }]}
        rowKey={(r) => r.id}
      />,
    );
    expect(screen.getByText("키보드")).toBeInTheDocument();
  });

  it("비어 있으면 안내 메시지를 표시한다", () => {
    render(<DataTable columns={columns} rows={[]} rowKey={(r) => r.id} emptyMessage="없음" />);
    expect(screen.getByText("없음")).toBeInTheDocument();
  });
});
