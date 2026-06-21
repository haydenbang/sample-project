import React from 'react'

interface Props {
  status: string
}

const colorMap: Record<string, string> = {
  active:       'background:#d1fae5;color:#065f46',
  inactive:     'background:#f3f4f6;color:#6b7280',
  pending:      'background:#fef3c7;color:#92400e',
  confirmed:    'background:#dbeafe;color:#1e40af',
  shipped:      'background:#ede9fe;color:#5b21b6',
  cancelled:    'background:#fee2e2;color:#991b1b',
  in_stock:     'background:#d1fae5;color:#065f46',
  out_of_stock: 'background:#fee2e2;color:#991b1b',
}

const labelMap: Record<string, string> = {
  active:       '활성',
  inactive:     '비활성',
  pending:      '대기중',
  confirmed:    '확인됨',
  shipped:      '배송중',
  cancelled:    '취소됨',
  in_stock:     '재고있음',
  out_of_stock: '품절',
}

export function StatusBadge({ status }: Props) {
  const style = colorMap[status] ?? 'background:#f3f4f6;color:#6b7280'
  const label = labelMap[status] ?? status
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 10px',
      borderRadius: 9999,
      fontSize: 12,
      fontWeight: 500,
      ...(Object.fromEntries(style.split(';').map(s => s.split(':') as [string, string]))),
    }}>
      {label}
    </span>
  )
}
