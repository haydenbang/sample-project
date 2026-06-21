// 회원 타입. 백엔드 schemas/user.py 및 db-schema.md 와 동기화.
// 컬럼/필드가 바뀌면 함께 변경되어야 한다. (scenario/db-schema-change)

export type UserRole = "ADMIN" | "STAFF" | "VIEWER";
export type UserGrade = "BRONZE" | "SILVER" | "GOLD" | "VIP";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  grade: UserGrade;
  is_active: boolean;
  created_at: string;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  size: number;
}
