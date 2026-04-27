import { NavLink, Outlet } from "react-router-dom";


const navItems = [
  { to: "/", label: "公开捐献" },
  { to: "/my", label: "我的凭证" },
  { to: "/admin", label: "审核后台" }
];

export function Layout() {
  return (
    <div className="app-shell">
      <div className="noise-layer" />
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">Gemini Contribution Relay</p>
          <h1>CPA Gemini 捐献站</h1>
        </div>
        <nav className="nav-ribbon" aria-label="主导航">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="page-frame">
        <Outlet />
      </main>
    </div>
  );
}

