import React, { useState } from 'react'
import { useUsers } from '../hooks/useUsers'
import UserForm from '../components/UserForm'
import { User, UserStatus } from '../types/user'

const STATUS_OPTIONS: { value: UserStatus | ''; label: string }[] = [
  { value: '', label: '전체' },
  { value: 'active', label: '활성' },
  { value: 'inactive', label: '비활성' },
  { value: 'suspended', label: '정지' },
  { value: 'pending', label: '대기' },
]

const STATUS_LABEL: Record<UserStatus, string> = {
  active: '활성',
  inactive: '비활성',
  suspended: '정지',
  pending: '대기',
}

const STATUS_COLOR: Record<UserStatus, string> = {
  active: 'green',
  inactive: 'gray',
  suspended: 'red',
  pending: 'orange',
}

export default function UsersPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [showForm, setShowForm] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const { users, loading, error } = useUsers(statusFilter)

  const handleSuccess = () => {
    setShowForm(false)
    setRefreshKey((k) => k + 1)
  }

  if (loading) return <div>로딩 중...</div>
  if (error) return <div style={{ color: 'red' }}>오류: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2>회원 관리</h2>
        <button onClick={() => setShowForm((v) => !v)}>
          {showForm ? '닫기' : '+ 회원 등록'}
        </button>
      </div>

      {showForm && <UserForm onSuccess={handleSuccess} />}

      <div style={{ marginBottom: 12 }}>
        <label>상태 필터: </label>
        <select value={statusFilter ?? ''} onChange={(e) => setStatusFilter(e.target.value || undefined)}>
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>아이디</th>
            <th>이메일</th>
            <th>상태</th>
            <th>등급</th>
            <th>가입일</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user: User) => (
            <tr key={user.id}>
              <td>{user.id}</td>
              <td>{user.username}</td>
              <td>{user.email}</td>
              <td>
                <span style={{ color: STATUS_COLOR[user.status] ?? 'gray' }}>
                  {STATUS_LABEL[user.status] ?? user.status}
                </span>
              </td>
              <td>{user.grade}</td>
              <td>{new Date(user.created_at).toLocaleDateString('ko-KR')}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {users.length === 0 && <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>회원이 없습니다.</div>}
    </div>
  )
}
