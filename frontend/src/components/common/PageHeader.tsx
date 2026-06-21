// 공통 페이지 헤더. 모든 페이지 상단에 사용된다.

import type { ReactNode } from "react";
import "./PageHeader.css";

export interface PageHeaderProps {
  title: string;
  description?: string;
  /** 우측 액션 영역 (버튼 등) */
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        <h1 className="page-header__title">{title}</h1>
        {description && <p className="page-header__desc">{description}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  );
}
