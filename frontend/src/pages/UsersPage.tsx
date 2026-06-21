import React, { useState } from 'react'
import { useUsers } from '../hooks/useUsers'
import { StatusBadge } from '../components/common/StatusBadge'
import { PageHeader } from '../components/common/PageHeader'
import { DataTable, Column } from '../components/common/DataTable'
import UserForm from '../components/UserForm'
import { User } from '../types/user'

export default function UsersPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [showForm, setShowForm] = useState(false)
  const { users, loading, error } = useUsers(statusFilter)

  const columns: Column<User>[] = [
    { key: 'id',         label: 'ID' },
    { key: 'username',   label: '아이디' },
    { key: 'email',      label: '이메일' },
    {
      key: 'status',
      label: '상태',
      render: (val: string) => <StatusBadge status={val} />,
    },
    {
      key: 'created_at',
      label: '가입일',
      render: (val: string) => new Date(val).toLocaleDateString('ko-KR'),
    },
  ]

  if (error) return <div style={{ color: 'red', padding: 24 }}>오류: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <PageHeader
        title="회원 관리"
        description="등록된 회원을 조회하고 관리합니다."
        action={
          <button onClick={() => setShowForm(v => !v)}>
            {showForm ? '닫기' : '+ 회원 등록'}
          </button>
        }
      />
      {showForm && <UserForm onSuccess={() => setShowForm(false)} />}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 14, marginRight: 8 }}>상태 필터:</label>
        <select value={statusFilter ?? ''} onChange={e => setStatusFilter(e.target.value || undefined)}>
          <option value="">전체</option>
          <option value="active">활성</option>
          <option value="inactive">비활성</option>
        </select>
      </div>
      <DataTable
        columns={columns}
        data={users}
        loading={loading}
        emptyMessage="등록된 회원이 없습니다."
      />
    </div>
  )
}
