import React, { useState } from 'react'
import { useUsers } from '../hooks/useUsers'
import UserForm from '../components/UserForm'
import { User } from '../types/user'

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
          <option value="">전체</option>
          <option value="active">활성</option>
          <option value="inactive">비활성</option>
        </select>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>아이디</th>
            <th>이메일</th>
            <th>상태</th>
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
                <span style={{ color: user.status === 'active' ? 'green' : 'gray' }}>
                  {user.status === 'active' ? '활성' : '비활성'}
                </span>
              </td>
              <td>{new Date(user.created_at).toLocaleDateString('ko-KR')}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {users.length === 0 && <div style={{ textAlign: 'center', padding: 32, color: '#999' }}>회원이 없습니다.</div>}
    </div>
  )
}
