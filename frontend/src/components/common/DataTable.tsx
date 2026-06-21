import React from 'react'

export interface Column<T> {
  key: keyof T
  label: string
  render?: (value: any, row: T) => React.ReactNode
}

interface Props<T> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyMessage?: string
}

const thStyle: React.CSSProperties = {
  padding: '10px 14px',
  textAlign: 'left',
  fontSize: 12,
  fontWeight: 600,
  color: '#6b7280',
  textTransform: 'uppercase',
  borderBottom: '1px solid #e5e7eb',
  background: '#f9fafb',
}

const tdStyle: React.CSSProperties = {
  padding: '10px 14px',
  fontSize: 14,
  color: '#111827',
  borderBottom: '1px solid #f3f4f6',
}

export function DataTable<T extends { id: number }>({ columns, data, loading, emptyMessage }: Props<T>) {
  if (loading) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af' }}>불러오는 중...</div>
  }
  if (!data.length) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af' }}>{emptyMessage ?? '데이터가 없습니다.'}</div>
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            {columns.map(col => (
              <th key={String(col.key)} style={thStyle}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.id} style={{ background: '#fff' }}>
              {columns.map(col => (
                <td key={String(col.key)} style={tdStyle}>
                  {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
