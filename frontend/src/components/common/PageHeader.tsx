import React from 'react'

interface Props {
  title: string
  description?: string
  action?: React.ReactNode
}

export function PageHeader({ title, description, action }: Props) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
      <div>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{title}</h2>
        {description && <p style={{ margin: '4px 0 0', fontSize: 14, color: '#6b7280' }}>{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
