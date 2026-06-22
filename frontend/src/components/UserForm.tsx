import React, { useState } from 'react'
import { UserCreate } from '../types/user'
import { createUser } from '../hooks/useUsers'

interface UserFormProps {
  onSuccess?: () => void
}

export default function UserForm({ onSuccess }: UserFormProps) {
  const [form, setForm] = useState<UserCreate>({ username: '', email: '', password: '', phone: '' })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await createUser(form)
      setForm({ username: '', email: '', password: '', phone: '' })
      onSuccess?.()
    } catch (err: any) {
      setError(err.response?.data?.detail ?? '회원 등록에 실패했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 400 }}>
      <h3>신규 회원 등록</h3>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <input
        name="username"
        placeholder="아이디"
        value={form.username}
        onChange={handleChange}
        required
      />
      <input
        name="email"
        type="email"
        placeholder="이메일"
        value={form.email}
        onChange={handleChange}
        required
      />
      <input
        name="password"
        type="password"
        placeholder="비밀번호"
        value={form.password}
        onChange={handleChange}
        required
      />
      <input
        name="phone"
        type="tel"
        placeholder="전화번호 (선택)"
        value={form.phone ?? ''}
        onChange={handleChange}
      />
      <button type="submit" disabled={submitting}>
        {submitting ? '등록 중...' : '등록'}
      </button>
    </form>
  )
}
