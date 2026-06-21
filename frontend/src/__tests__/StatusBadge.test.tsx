import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StatusBadge } from '../components/common/StatusBadge'

describe('StatusBadge', () => {
  it('active 상태의 한글 라벨을 렌더링한다', () => {
    render(<StatusBadge status="active" />)
    expect(screen.getByText('활성')).toBeInTheDocument()
  })

  it('pending 상태를 렌더링한다', () => {
    render(<StatusBadge status="pending" />)
    expect(screen.getByText('대기중')).toBeInTheDocument()
  })

  it('cancelled 상태를 렌더링한다', () => {
    render(<StatusBadge status="cancelled" />)
    expect(screen.getByText('취소됨')).toBeInTheDocument()
  })

  it('알 수 없는 status는 그대로 표시한다', () => {
    render(<StatusBadge status="unknown_status" />)
    expect(screen.getByText('unknown_status')).toBeInTheDocument()
  })
})
