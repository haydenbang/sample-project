import React, { useState } from 'react'
import { UserCreate, UserGrade } from '../types/user'
import { createUser } from '../hooks/useUsers'

interface UserFormProps {
  onSuccess?: () => void
}

const GRADE_OPTIONS: { value: UserGrade; label: string }[] = [
  { value: 'bronze', label: '브론즈' },
  { value: 'silver', label: '실버' },
  { value: 'gold', label: '골드' },
  { value: 'platinum', label: '플래티넘' },
]

export default function UserForm({ onSuccess }: UserFormProps) {
  const [form, setForm] = useState<UserCreate>({ username: '', email: '', password: '' })
  const [grade, setGrade] = useState<UserGrade>('bronze')
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
      await createUser({ ...form, grade })
      setForm({ username: '', email: '', password: '' })
      setGrade('bronze')
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
      <div>
        <label>등급: </label>
        <select value={grade} onChange={(e) => setGrade(e.target.value as UserGrade)}>
          {GRADE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      <button type="submit" disabled={submitting}>
        {submitting ? '등록 중...' : '등록'}
      </button>
    </form>
  )
}
