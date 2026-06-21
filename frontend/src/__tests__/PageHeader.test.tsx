import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PageHeader } from '../components/common/PageHeader'

describe('PageHeader', () => {
  it('title을 렌더링한다', () => {
    render(<PageHeader title="회원 관리" />)
    expect(screen.getByText('회원 관리')).toBeInTheDocument()
  })

  it('description이 있으면 표시한다', () => {
    render(<PageHeader title="테스트" description="페이지 설명" />)
    expect(screen.getByText('페이지 설명')).toBeInTheDocument()
  })

  it('description 없으면 렌더링하지 않는다', () => {
    render(<PageHeader title="테스트" />)
    expect(screen.queryByText('페이지 설명')).not.toBeInTheDocument()
  })

  it('action 슬롯이 렌더링된다', () => {
    render(<PageHeader title="테스트" action={<button>추가</button>} />)
    expect(screen.getByText('추가')).toBeInTheDocument()
  })
})
