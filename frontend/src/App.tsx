// 앱 셸: 네비게이션 + 라우팅.

import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { OrdersPage } from "./pages/OrdersPage";
import { ProductsPage } from "./pages/ProductsPage";
import { UsersPage } from "./pages/UsersPage";

export default function App() {
  return (
    <div className="app">
      <aside className="app__sidebar">
        <h2 className="app__logo">ShopAdmin</h2>
        <nav className="app__nav">
          <NavLink to="/products">상품</NavLink>
          <NavLink to="/orders">주문</NavLink>
          <NavLink to="/users">회원</NavLink>
        </nav>
      </aside>
      <main className="app__content">
        <Routes>
          <Route path="/" element={<Navigate to="/products" replace />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Routes>
      </main>
    </div>
  );
}
